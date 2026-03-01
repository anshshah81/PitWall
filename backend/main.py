"""
PitWall FastAPI Application
Main API server for F1 race strategy optimization
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models.schemas import RaceConfig, OptimizeResponse, TeamInfo, DriverInfo, Strategy, EmergencyPitAdvice
from engine.optimizer import optimize
from engine.monte_carlo import score_top_strategies
from ai.race_engineer import generate_brief
import json
import os
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="PitWall API",
    description="F1 Race Strategy Optimizer",
    version="1.0.0"
)

# CORS middleware for frontend (localhost + Vercel deployments)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load track metadata
TRACKS = {}
try:
    with open("data/tracks.json") as f:
        TRACKS = json.load(f)
except FileNotFoundError:
    print("Warning: data/tracks.json not found. Using empty tracks dict.")

# Load team metadata
TEAMS = {}
try:
    with open("data/teams.json") as f:
        TEAMS = json.load(f)
except FileNotFoundError:
    print("Warning: data/teams.json not found. Using empty teams dict.")

# Load testing data (if available)
TESTING_DATA = {}
try:
    with open("data/testing_data.json") as f:
        TESTING_DATA = json.load(f)
except FileNotFoundError:
    print("Info: data/testing_data.json not found. Testing data not available.")


def _build_team_info(team_id: str, team_data: dict) -> TeamInfo:
    """Build a TeamInfo from raw team JSON data."""
    drivers_dict = {}
    for d_id, d_data in team_data["drivers"].items():
        drivers_dict[d_id] = DriverInfo(
            id=d_id,
            name=d_data["name"],
            number=d_data["number"],
            pace_delta=d_data["pace_delta"],
            tire_management=d_data["tire_management"],
            wet_skill=d_data["wet_skill"],
            consistency=d_data["consistency"],
            overtaking_delta=d_data["overtaking_delta"],
        )
    return TeamInfo(
        id=team_id,
        name=team_data["name"],
        short=team_data["short"],
        color=team_data["color"],
        base_delta=team_data["base_delta"],
        pit_crew_delta=team_data["pit_crew_delta"],
        tire_wear_factor=team_data["tire_wear_factor"],
        drivers=drivers_dict,
    )


def _get_driver_names(team_data: dict) -> list:
    """Extract driver full names from team data."""
    return [d["name"] for d in team_data["drivers"].values()]


def _rain_advice(config: RaceConfig) -> tuple[str, str]:
    """Recommended compound and summary if it's raining when the driver has to pit in an emergency."""
    rain_prob = getattr(config, "rain_probability", 0) or 0
    if rain_prob >= 0.5:
        return (
            "WET",
            "Take WET if standing water; otherwise INTERMEDIATE. Switch to dry compound when track dries.",
        )
    return (
        "INTERMEDIATE",
        "Take INTERMEDIATE (or WET if heavy rain). Switch to dry compound when track dries.",
    )


def _compute_emergency_advice(optimal: Strategy, config: RaceConfig) -> list[EmergencyPitAdvice]:
    """
    For each lap window *between* the recommended pit stops, recommend what to do
    if the driver is forced to pit in that window (safety car, puncture, damage).
    Always includes rain option: if it's raining when you pit, use INTERMEDIATE/WET.
    """
    advice: list[EmergencyPitAdvice] = []
    stops = optimal.stops
    total_laps = config.total_laps
    compound_rain, summary_rain = _rain_advice(config)

    # Build windows: before first stop, between stop 1 and 2, etc.
    pit_laps = sorted([s.lap for s in stops])
    compounds_by_lap = {s.lap: s.compound.value for s in stops}

    # Window 1: laps 1 to (first pit - 1) — split early vs late so it doesn't always default to hard to the end
    if pit_laps:
        first_stop = pit_laps[0]
        if first_stop > 1:
            lap_end = first_stop - 1
            c1 = compounds_by_lap.get(pit_laps[0], "MEDIUM")
            is_one_stop = len(pit_laps) < 2

            # Early in the window (many laps still to go): prefer MEDIUM + second stop instead of one long stint on HARD
            early_cutoff = max(1, first_stop - 12)  # e.g. laps 1–5 for first_stop=18
            if early_cutoff >= 1 and lap_end >= early_cutoff:
                lap_range_early = f"1–{early_cutoff}"
                if is_one_stop and c1 == "HARD":
                    # 1-stop plan was HARD to the end; for early emergency pit, suggest 2 stops to avoid 50+ laps on HARD
                    second_stop_lap = first_stop + (total_laps - first_stop) // 2
                    advice.append(
                        EmergencyPitAdvice(
                            lap_range=lap_range_early,
                            scenario="Safety car, puncture, or damage very early (before first planned stop)",
                            compound="MEDIUM",
                            summary=f"Take MEDIUM; then one more stop for HARD around lap {second_stop_lap} (2 stops total).",
                            compound_if_rain=compound_rain,
                            summary_if_rain=summary_rain,
                        )
                    )
                elif is_one_stop:
                    advice.append(
                        EmergencyPitAdvice(
                            lap_range=lap_range_early,
                            scenario="Safety car, puncture, or damage very early (before first planned stop)",
                            compound=c1,
                            summary=f"Take {c1} and run to the end (1 stop total).",
                            compound_if_rain=compound_rain,
                            summary_if_rain=summary_rain,
                        )
                    )
                else:
                    c2 = compounds_by_lap.get(pit_laps[1], "HARD")
                    advice.append(
                        EmergencyPitAdvice(
                            lap_range=lap_range_early,
                            scenario="Safety car, puncture, or damage very early (before first planned stop)",
                            compound=c1,
                            summary=f"Take {c1}; then one more stop for {c2} around lap {pit_laps[1]} to rejoin plan.",
                            compound_if_rain=compound_rain,
                            summary_if_rain=summary_rain,
                        )
                    )

            # Late in the window (close to planned first stop): take planned compound to the end or rejoin plan
            late_start = early_cutoff + 1
            if late_start <= lap_end:
                lap_range_late = f"{late_start}–{lap_end}"
                if is_one_stop:
                    advice.append(
                        EmergencyPitAdvice(
                            lap_range=lap_range_late,
                            scenario="Safety car, puncture, or damage shortly before your planned stop",
                            compound=c1,
                            summary=f"Take {c1} and run to the end (1 stop total).",
                            compound_if_rain=compound_rain,
                            summary_if_rain=summary_rain,
                        )
                    )
                else:
                    c2 = compounds_by_lap.get(pit_laps[1], "HARD")
                    advice.append(
                        EmergencyPitAdvice(
                            lap_range=lap_range_late,
                            scenario="Safety car, puncture, or damage shortly before your first planned stop",
                            compound=c1,
                            summary=f"Take {c1}; then one more stop for {c2} around lap {pit_laps[1]} to rejoin plan.",
                            compound_if_rain=compound_rain,
                            summary_if_rain=summary_rain,
                        )
                    )

    # Window 2, 3, ...: between consecutive planned stops
    for i in range(len(pit_laps) - 1):
        start = pit_laps[i] + 1
        end = pit_laps[i + 1] - 1
        if start > end:
            continue
        lap_range = f"{start}–{end}"
        # Recommend the next planned compound (what they'd take at the next stop), then to the end
        next_compound = compounds_by_lap.get(pit_laps[i + 1], "HARD")
        advice.append(
            EmergencyPitAdvice(
                lap_range=lap_range,
                scenario="Safety car or unscheduled pit between your planned stops",
                compound=next_compound,
                summary=f"Take {next_compound} and run to the end (no more stops).",
            )
        )

    # Window after last stop to end of race: unscheduled pit in final stint
    if pit_laps:
        last_stop = pit_laps[-1]
        start = last_stop + 1
        if start <= total_laps:
            laps_in_window = total_laps - start + 1
            # Final laps (e.g. last 12): recommend SOFT for max grip on short run to the flag
            soft_cutoff = 12
            if laps_in_window > soft_cutoff:
                # Early/mid part of window: HARD or MEDIUM to the end
                early_end = total_laps - soft_cutoff
                lap_range_early = f"{start}–{early_end}"
                if laps_in_window > 22:
                    compound_early, summary_early = "HARD", "Take HARD and run to the end (no more stops)."
                else:
                    compound_early, summary_early = "MEDIUM", "Take MEDIUM and run to the end (no more stops)."
                advice.append(
                    EmergencyPitAdvice(
                        lap_range=lap_range_early,
                        scenario="Puncture or damage after your last planned stop (earlier in final stint)",
                        compound=compound_early,
                        summary=summary_early,
                        compound_if_rain=compound_rain,
                        summary_if_rain=summary_rain,
                    )
                )
            # Range at the end of the race: switch to SOFT for the short run to the flag
            end_range_start = max(start, total_laps - soft_cutoff + 1)
            if end_range_start <= total_laps:
                lap_range_end = f"{end_range_start}–{total_laps}"
                advice.append(
                    EmergencyPitAdvice(
                        lap_range=lap_range_end,
                        scenario="Puncture or damage in the final laps after your last planned stop",
                        compound="SOFT",
                        summary="Take SOFT to the end; maximum grip for the short run to the flag (no more stops).",
                        compound_if_rain=compound_rain,
                        summary_if_rain=summary_rain,
                    )
                )

    return advice


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "name": "PitWall API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok"}


@app.get("/tracks")
def get_tracks():
    """Get list of available tracks with metadata including weather data"""
    tracks_list = []
    for track_id, data in TRACKS.items():
        tracks_list.append({
            "id": track_id,
            "name": data.get("name", track_id.replace("_", " ").title()),
            "circuit": data.get("circuit", ""),
            "laps": data.get("laps", 57),
            "pit_loss": data.get("pit_loss", 22.0),
            "base_lap_time": data.get("base_lap_time", 90.0),
            "race_month": data.get("race_month", 6),
            "historical_rain_pct": data.get("historical_rain_pct", 0.15),
            "rain_intensity": data.get("rain_intensity", "moderate"),
            "historical_safety_car_pct": data.get("historical_safety_car_pct", 0.2),
            "recommended_start_compound": data.get("recommended_start_compound", "SOFT"),
        })
    return {"tracks": tracks_list}


@app.get("/teams")
def get_teams():
    """Get list of all 2026 F1 teams with metadata and driver details"""
    teams_list = []
    for team_id, data in TEAMS.items():
        teams_list.append(_build_team_info(team_id, data))
    # Sort by performance (base_delta ascending = fastest first)
    teams_list.sort(key=lambda t: t.base_delta)
    return {"teams": teams_list}


@app.get("/teams/{team_id}")
def get_team(team_id: str):
    """Get a specific team's data"""
    if team_id not in TEAMS:
        raise HTTPException(
            status_code=404,
            detail=f"Team '{team_id}' not found. Available: {list(TEAMS.keys())}"
        )
    return _build_team_info(team_id, TEAMS[team_id])


@app.get("/testing")
def get_testing_data():
    """Get preseason testing data for all teams"""
    if not TESTING_DATA:
        raise HTTPException(
            status_code=404,
            detail="No testing data available. Run data_prep/fetch_reference_data.py first."
        )
    return {"testing_sessions": TESTING_DATA}


@app.get("/testing/{team_id}")
def get_team_testing_data(team_id: str):
    """Get preseason testing data for a specific team"""
    if team_id not in TEAMS:
        raise HTTPException(
            status_code=404,
            detail=f"Team '{team_id}' not found."
        )
    
    team_name = TEAMS[team_id]["name"]
    team_testing = {}
    
    for session_key, session_data in TESTING_DATA.items():
        teams_in_session = session_data.get("teams", {})
        # Match by team name (testing data uses full names)
        for t_name, t_data in teams_in_session.items():
            if t_name == team_name or team_name.startswith(t_name) or t_name.startswith(team_name.split()[0]):
                team_testing[session_key] = t_data
                break
    
    return {
        "team_id": team_id,
        "team_name": team_name,
        "testing_data": team_testing
    }


@app.post("/optimize", response_model=OptimizeResponse)
def run_optimization(config: RaceConfig):
    """
    Main optimization endpoint.
    
    Takes race configuration, runs:
      1. Convergent beam-search optimizer (seeds extremes → refines to optimal)
      2. Monte Carlo scorer (exact rain % matching, safety car injection)
      3. AI brief from Claude
    
    Returns top 20 strategies with robustness scores and AI brief.
    Two strategies are tagged: OPTIMAL (best P50) and VARIABLE (best robustness).
    """
    try:
        # Validate track exists
        if config.track not in TRACKS:
            raise HTTPException(
                status_code=400,
                detail=f"Track '{config.track}' not found. Available: {list(TRACKS.keys())}"
            )
        
        # If total_laps not provided, use track default
        if not config.total_laps or config.total_laps == 0:
            config.total_laps = TRACKS[config.track]["laps"]
        
        # Get track weather info for logging
        track_weather = TRACKS[config.track]
        rain_pct = config.rain_probability * 100
        rain_int = track_weather.get("rain_intensity", "moderate")
        
        # Use track's historical safety car probability (overrides client value)
        historical_sc = track_weather.get("historical_safety_car_pct")
        if historical_sc is not None:
            config = config.model_copy(update={"safety_car_probability": historical_sc})
        
        # Get team data if specified
        team_data = None
        team_info = None
        if config.team and config.team in TEAMS:
            team_data = TEAMS[config.team]
            team_info = _build_team_info(config.team, team_data)
            print(f"Optimizing for {team_data['name']} at {config.track}, {config.total_laps} laps...")
            print(f"  Team delta: +{team_data['base_delta']}s base, +{team_data['pit_crew_delta']}s pit, {team_data['tire_wear_factor']}x tire wear")
        else:
            print(f"Optimizing for generic car at {config.track}, {config.total_laps} laps...")
        
        # Get driver data if specified
        driver_data = None
        driver_info = None
        if config.driver and team_data:
            drivers = team_data.get("drivers", {})
            if config.driver in drivers:
                driver_data = drivers[config.driver]
                driver_info = DriverInfo(
                    id=config.driver,
                    name=driver_data["name"],
                    number=driver_data["number"],
                    pace_delta=driver_data["pace_delta"],
                    tire_management=driver_data["tire_management"],
                    wet_skill=driver_data["wet_skill"],
                    consistency=driver_data["consistency"],
                    overtaking_delta=driver_data["overtaking_delta"],
                )
                print(f"  Driver: {driver_data['name']} #{driver_data['number']}")
                print(f"    Pace: +{driver_data['pace_delta']:.2f}s | Tire mgmt: {driver_data['tire_management']:.2f}x | Wet: {driver_data['wet_skill']:.2f}x | Consistency: {driver_data['consistency']:.2f}x | Overtaking: {driver_data['overtaking_delta']:+.2f}s")
            else:
                print(f"  Warning: Driver '{config.driver}' not found in team. Using team average.")
        
        print(f"  Rain: {rain_pct:.0f}% probability, intensity={rain_int}")
        print(f"  Safety car: {config.safety_car_probability * 100:.0f}% probability")
        
        # Step 1: Run convergent beam-search optimizer → top 20 candidates
        print("  Running convergent optimizer...")
        candidates = optimize(config, team_data=team_data, driver_data=driver_data)
        print(f"  Top {len(candidates)} candidates selected")
        
        # Step 2: Score with Monte Carlo → top 20 Strategy objects (tagged OPTIMAL / VARIABLE)
        # Rain matching: exactly {rain_pct}% of 500 sims have rain
        print(f"  Running Monte Carlo (500 sims, {round(500 * config.rain_probability)} rainy)...")
        strategies = score_top_strategies(config, candidates, team_data=team_data, driver_data=driver_data)
        print(f"  {len(strategies)} strategies scored and tagged")
        
        # Step 3: Generate AI brief for the OPTIMAL strategy
        optimal_strategy = next((s for s in strategies if s.tag == "OPTIMAL"), strategies[0])
        driver_names = _get_driver_names(team_data) if team_data else None
        
        # If a specific driver is selected, emphasize them in the brief
        selected_driver_name = driver_data["name"] if driver_data else None
        
        print("  Generating AI brief...")
        brief = generate_brief(
            optimal_strategy, config,
            team_name=team_data["name"] if team_data else None,
            drivers=driver_names,
            selected_driver=selected_driver_name,
            driver_traits=driver_data,
        )

        # Emergency / contingency pit advice for windows between recommended stops
        emergency_advice = _compute_emergency_advice(optimal_strategy, config)
        print(f"  Emergency advice: {len(emergency_advice)} contingency windows")

        print("  Optimization complete!")

        return OptimizeResponse(
            strategies=strategies,
            ai_brief=brief,
            config=config,
            team_info=team_info,
            driver_info=driver_info,
            emergency_advice=emergency_advice,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error during optimization: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
