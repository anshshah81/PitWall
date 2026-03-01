"""
Calibrate team performance from real FastF1 data.
Attempts 2026 preseason testing first, falls back to 2025/2024 race data.

Outputs updated teams.json with data-driven pace deltas, pit crew deltas,
and tire wear factors.

Usage:
    cd data_prep
    python calibrate_from_testing.py
"""

import fastf1
import numpy as np
import pandas as pd
import json
import os
import sys
import warnings

# Suppress FastF1 warnings about fuzzy matching
warnings.filterwarnings('ignore', category=UserWarning)

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

fastf1.Cache.enable_cache('../backend/data/cache')

# --- Configuration -----------------------------------------------------------

# We need to discover what events are available per year first
# rather than guessing event names

# 2024 race data as reliable fallback (known to work)
RACES_2024 = [
    (2024, 'Bahrain', 'R'),
    (2024, 'Spain', 'R'),
    (2024, 'Monaco', 'R'),
    (2024, 'Silverstone', 'R'),
    (2024, 'Monza', 'R'),
]

# Map FastF1 team names -> our team IDs in teams.json
TEAM_NAME_MAP = {
    # 2024-2026 names
    'Red Bull Racing': 'red_bull',
    'Red Bull': 'red_bull',
    'Ferrari': 'ferrari',
    'Scuderia Ferrari': 'ferrari',
    'McLaren': 'mclaren',
    'Mercedes': 'mercedes',
    'Aston Martin': 'aston_martin',
    'Alpine': 'alpine',
    'RB': 'rb',
    'AlphaTauri': 'rb',
    'Racing Bulls': 'rb',
    'Visa Cash App RB': 'rb',
    'Haas F1 Team': 'haas',
    'Haas': 'haas',
    'Williams': 'williams',
    'Kick Sauber': 'sauber',
    'Sauber': 'sauber',
    'Alfa Romeo': 'sauber',
    'Cadillac': 'cadillac',
    'Cadillac F1': 'cadillac',
    'General Motors': 'cadillac',
}

TEAMS_JSON_PATH = '../backend/data/teams.json'
TESTING_DATA_PATH = '../backend/data/testing_data.json'


# --- Discover Available Sessions ---------------------------------------------

def discover_events(year):
    """
    Use FastF1's event schedule to discover what sessions exist for a year.
    Returns list of (year, event_name, session_type) tuples.
    """
    print(f"\n  Discovering {year} event schedule...")
    try:
        schedule = fastf1.get_event_schedule(year)
        events = []
        for _, row in schedule.iterrows():
            event_name = row.get('EventName', '')
            event_format = row.get('EventFormat', '')
            if event_name:
                events.append({
                    'name': event_name,
                    'format': event_format,
                })
        print(f"    Found {len(events)} events for {year}")
        
        # Print all events so we can see what's available
        for ev in events:
            tag = " [TESTING]" if 'test' in ev['name'].lower() else ""
            print(f"      - {ev['name']} ({ev['format']}){tag}")
        
        return events
    except Exception as e:
        print(f"    Failed to get {year} schedule: {str(e)[:80]}")
        return []


def find_testing_sessions(year):
    """
    Find pre-season testing sessions for a given year.
    Returns list of (year, event_name, session_id) tuples.
    """
    events = discover_events(year)
    testing_sessions = []
    
    for ev in events:
        name = ev['name']
        if 'test' in name.lower():
            # Testing events typically have sessions 1, 2, 3 (one per day)
            for day in [1, 2, 3]:
                testing_sessions.append((year, name, day))
    
    return testing_sessions


def find_race_sessions(year, max_races=5):
    """
    Find race sessions for a given year.
    Returns list of (year, event_name, 'R') tuples.
    """
    events = discover_events(year)
    race_sessions = []
    
    for ev in events:
        name = ev['name']
        fmt = ev.get('format', '')
        # Skip testing events
        if 'test' in name.lower():
            continue
        race_sessions.append((year, name, 'R'))
        if len(race_sessions) >= max_races:
            break
    
    return race_sessions


# --- Data Extraction Functions -----------------------------------------------

def resolve_team_id(fastf1_name):
    """Map a FastF1 team name to our team ID."""
    if not fastf1_name or pd.isna(fastf1_name):
        return None
    fastf1_name = str(fastf1_name)
    # Exact match first
    if fastf1_name in TEAM_NAME_MAP:
        return TEAM_NAME_MAP[fastf1_name]
    # Partial match
    for key, value in TEAM_NAME_MAP.items():
        if key.lower() in fastf1_name.lower() or fastf1_name.lower() in key.lower():
            return value
    return None


def get_clean_laps(laps_df):
    """
    Filter to clean laps only: no pit in/out, no lap 1, reasonable times.
    Works for both race and testing sessions.
    """
    clean = laps_df[
        (laps_df['LapTime'].notna()) &
        (laps_df['PitInTime'].isna()) &
        (laps_df['PitOutTime'].isna())
    ].copy()
    
    # Remove lap 1 if LapNumber exists
    if 'LapNumber' in clean.columns:
        clean = clean[clean['LapNumber'] > 1]
    
    # Convert to seconds
    clean['LapSeconds'] = clean['LapTime'].dt.total_seconds()
    
    # Remove install laps (< 60s)
    clean = clean[clean['LapSeconds'] > 60]
    
    result = []
    for team in clean['Team'].dropna().unique():
        t_laps = clean[clean['Team'] == team].copy()
        if len(t_laps) < 3:
            continue
        median = t_laps['LapSeconds'].median()
        # Remove outliers: > 115% of team median
        t_clean = t_laps[t_laps['LapSeconds'] < median * 1.15]
        if len(t_clean) >= 3:
            result.append(t_clean)
    
    return pd.concat(result) if result else pd.DataFrame()


def compute_pace_gaps(clean_laps):
    """Compute pace delta per team from clean laps. Returns {team_id: delta_seconds}."""
    team_paces = {}
    for team in clean_laps['Team'].dropna().unique():
        team_id = resolve_team_id(team)
        if team_id is None:
            print(f"    [!] Unknown team: '{team}' -- skipping")
            continue
        t_laps = clean_laps[clean_laps['Team'] == team]
        if len(t_laps) >= 5:
            # Use 10th percentile as representative pace (best realistic laps)
            team_paces[team_id] = float(np.percentile(t_laps['LapSeconds'], 10))
    
    if not team_paces:
        return {}
    
    # Convert to deltas from fastest
    fastest = min(team_paces.values())
    return {t: round(v - fastest, 3) for t, v in team_paces.items()}


def compute_pit_deltas(laps_df):
    """Compute average pit stop duration delta per team."""
    pit_laps = laps_df[
        laps_df['PitOutTime'].notna() & 
        laps_df['PitInTime'].notna()
    ].copy()
    
    if len(pit_laps) == 0:
        return {}
    
    team_pit_times = {}
    for _, lap in pit_laps.iterrows():
        team = lap.get('Team')
        if pd.isna(team):
            continue
        team_id = resolve_team_id(team)
        if team_id is None:
            continue
        try:
            duration = (lap['PitOutTime'] - lap['PitInTime']).total_seconds()
            if 15 < duration < 40:  # Reasonable pit stop range
                team_pit_times.setdefault(team_id, []).append(duration)
        except Exception:
            continue
    
    if not team_pit_times:
        return {}
    
    avg_times = {t: float(np.median(times)) for t, times in team_pit_times.items() if len(times) >= 2}
    
    if not avg_times:
        return {}
    
    fastest_pit = min(avg_times.values())
    return {t: round(v - fastest_pit, 2) for t, v in avg_times.items()}


def compute_tire_wear_factors(clean_laps):
    """
    Estimate tire wear factor per team by comparing degradation slopes.
    Higher slope = worse tire management = higher wear factor.
    """
    team_slopes = {}
    
    for team in clean_laps['Team'].dropna().unique():
        team_id = resolve_team_id(team)
        if team_id is None:
            continue
        
        t_laps = clean_laps[clean_laps['Team'] == team].copy()
        
        if 'TyreLife' not in t_laps.columns or len(t_laps) < 10:
            continue
        
        tyre_life = t_laps['TyreLife'].values.astype(float)
        lap_seconds = t_laps['LapSeconds'].values.astype(float)
        
        # Only use laps where tire life > 3 (past warm-up) and < 30 (before cliff)
        mask = (tyre_life > 3) & (tyre_life < 30) & np.isfinite(tyre_life) & np.isfinite(lap_seconds)
        if mask.sum() < 5:
            continue
        
        try:
            coeffs = np.polyfit(tyre_life[mask], lap_seconds[mask], 1)
            slope = coeffs[0]  # seconds per lap of tire age
            if slope > 0:
                team_slopes[team_id] = slope
        except Exception:
            continue
    
    if not team_slopes:
        return {}
    
    # Normalize: lowest degradation team's slope = 1.0 baseline
    min_slope = min(team_slopes.values())
    max_slope = max(team_slopes.values())
    if min_slope <= 0:
        return {}
    
    raw_ratios = {t: v / min_slope for t, v in team_slopes.items()}
    
    # Compress into realistic range [1.0, 1.15]
    # In reality, tire wear differences between F1 teams are ~5-15%,
    # but testing data has wildly varying programs (aero runs, race sims,
    # different fuel loads) that inflate the raw slope ratios.
    raw_max = max(raw_ratios.values())
    if raw_max <= 1.0:
        return {t: 1.0 for t in raw_ratios}
    
    WEAR_FLOOR = 1.0
    WEAR_CEILING = 1.15  # Max 15% worse tire wear than best team
    
    compressed = {}
    for t, raw in raw_ratios.items():
        # Linear map from [1.0, raw_max] to [1.0, 1.15]
        normalized = WEAR_FLOOR + (raw - 1.0) / (raw_max - 1.0) * (WEAR_CEILING - WEAR_FLOOR)
        compressed[t] = round(normalized, 3)
    
    return compressed


def extract_testing_json(session, session_label):
    """Extract testing data in the format expected by testing_data.json."""
    try:
        laps = session.laps
    except Exception:
        return {}
    
    if laps is None or len(laps) == 0:
        return {}
    
    teams_data = {}
    for team in laps['Team'].dropna().unique():
        t_laps = laps[
            (laps['Team'] == team) &
            (laps['LapTime'].notna()) &
            (laps['PitInTime'].isna()) &
            (laps['PitOutTime'].isna())
        ].copy()
        
        if len(t_laps) == 0:
            continue
        
        lap_times = t_laps['LapTime'].dt.total_seconds()
        median_time = lap_times.median()
        clean_times = lap_times[(lap_times > 60) & (lap_times < median_time * 1.3)]
        
        if len(clean_times) == 0:
            continue
        
        # Per-compound breakdown
        compound_data = {}
        if 'Compound' in t_laps.columns:
            for compound in t_laps['Compound'].dropna().unique():
                c_laps = t_laps[t_laps['Compound'] == compound]
                c_times = c_laps['LapTime'].dt.total_seconds()
                c_clean = c_times[(c_times > 60) & (c_times < median_time * 1.3)]
                if len(c_clean) > 0:
                    compound_data[str(compound)] = {
                        "best": round(float(c_clean.min()), 3),
                        "mean": round(float(c_clean.mean()), 3),
                        "count": int(len(c_clean))
                    }
        
        # Per-driver breakdown
        driver_data = {}
        if 'Driver' in t_laps.columns:
            for driver in t_laps['Driver'].dropna().unique():
                d_laps = t_laps[t_laps['Driver'] == driver]
                d_times = d_laps['LapTime'].dt.total_seconds()
                d_clean = d_times[(d_times > 60) & (d_times < median_time * 1.3)]
                if len(d_clean) > 0:
                    driver_data[str(driver)] = {
                        "best": round(float(d_clean.min()), 3),
                        "mean": round(float(d_clean.mean()), 3),
                        "count": int(len(d_clean))
                    }
        
        teams_data[str(team)] = {
            "best_lap": round(float(clean_times.min()), 3),
            "mean_lap": round(float(clean_times.mean()), 3),
            "median_lap": round(float(clean_times.median()), 3),
            "total_laps": int(len(clean_times)),
            "compounds": compound_data,
            "drivers": driver_data,
        }
    
    return teams_data


# --- Session Loading Functions -----------------------------------------------

def try_load_sessions(session_list, label):
    """
    Try loading sessions from a list of (year, event, session) tuples.
    Returns (all_clean_laps, all_raw_laps, testing_json_data, source_label).
    """
    print(f"\n{'='*60}")
    print(f"  ATTEMPTING: {label}")
    print(f"{'='*60}")
    
    all_clean = []
    all_raw = []
    testing_json = {}
    sessions_loaded = 0
    
    for year, event, session_id in session_list:
        session_label = f"{year} {event} (session {session_id})"
        print(f"\n  Trying {session_label}...")
        try:
            session = fastf1.get_session(year, event, session_id)
            session.load()
            
            try:
                laps = session.laps
                n_laps = len(laps) if laps is not None else 0
            except Exception:
                n_laps = 0
            
            if n_laps == 0:
                print(f"    [X] No laps found")
                continue
            
            print(f"    [OK] {n_laps} total laps loaded")
            sessions_loaded += 1
            
            # Get clean laps for pace analysis
            clean = get_clean_laps(laps)
            if len(clean) > 0:
                all_clean.append(clean)
                print(f"    [OK] {len(clean)} clean laps extracted")
            
            # Keep raw laps for pit stop analysis
            all_raw.append(laps.copy())
            
            # Extract testing JSON format
            t_data = extract_testing_json(session, session_label)
            if t_data:
                key = f"{year}_session{session_id}"
                testing_json[key] = {
                    "year": year,
                    "day": session_id if isinstance(session_id, int) else 0,
                    "event": str(event),
                    "teams": t_data
                }
                print(f"    [OK] Testing data extracted for {len(t_data)} teams")
            
        except Exception as e:
            err_str = str(e)
            if 'not found' in err_str.lower() or 'no match' in err_str.lower():
                print(f"    [X] Session not available in FastF1")
            else:
                print(f"    [X] Error: {err_str[:120]}")
            continue
    
    if sessions_loaded == 0:
        print(f"\n  [X] No sessions loaded from {label}")
        return None, None, {}, label
    
    combined_clean = pd.concat(all_clean) if all_clean else pd.DataFrame()
    combined_raw = pd.concat(all_raw) if all_raw else pd.DataFrame()
    
    print(f"\n  [OK] {sessions_loaded} sessions loaded, {len(combined_clean)} total clean laps")
    return combined_clean, combined_raw, testing_json, label


# --- Main --------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  PitWall -- Team Performance Calibration")
    print("  Attempting real data from FastF1")
    print("=" * 60)
    
    # Step 1: Discover what's available for 2026 and 2025
    sessions_2026_testing = find_testing_sessions(2026)
    sessions_2026_races = find_race_sessions(2026, max_races=5) if not sessions_2026_testing else []
    sessions_2025_testing = find_testing_sessions(2025)
    sessions_2025_races = find_race_sessions(2025, max_races=5)
    
    # Build priority list
    data_sources = []
    if sessions_2026_testing:
        data_sources.append((sessions_2026_testing, "2026 Pre-Season Testing"))
    if sessions_2026_races:
        data_sources.append((sessions_2026_races, "2026 Race Data"))
    if sessions_2025_testing:
        data_sources.append((sessions_2025_testing, "2025 Pre-Season Testing"))
    if sessions_2025_races:
        data_sources.append((sessions_2025_races, "2025 Race Data"))
    # Always have 2024 as fallback
    data_sources.append((RACES_2024, "2024 Race Data (fallback)"))
    
    print(f"\n  Data source priority ({len(data_sources)} sources):")
    for i, (sessions, label) in enumerate(data_sources):
        print(f"    {i+1}. {label} ({len(sessions)} sessions)")
    
    # Step 2: Try each source in priority order
    clean_laps = None
    raw_laps = None
    testing_json = {}
    source_used = None
    
    for sessions, label in data_sources:
        clean, raw, t_json, src = try_load_sessions(sessions, label)
        
        if clean is not None and len(clean) > 0:
            clean_laps = clean
            raw_laps = raw
            testing_json = t_json
            source_used = src
            print(f"\n  >> Using {src} as primary data source")
            break
        
        # Even if clean laps failed, save any testing JSON we got
        if t_json:
            testing_json.update(t_json)
    
    if clean_laps is None or len(clean_laps) == 0:
        print("\n" + "=" * 60)
        print("  [FAILED] No usable data found from any source.")
        print("  Keeping existing estimated values in teams.json")
        print("=" * 60)
        return
    
    # Step 3: Compute metrics
    print("\n" + "=" * 60)
    print(f"  COMPUTING METRICS from {source_used}")
    print("=" * 60)
    
    # 1. Pace gaps
    print("\n--- Pace Gaps (base_delta) ---")
    pace_gaps = compute_pace_gaps(clean_laps)
    for team, delta in sorted(pace_gaps.items(), key=lambda x: x[1]):
        print(f"  {team:15s}: +{delta:.3f}s/lap")
    
    # 2. Pit stop deltas
    print("\n--- Pit Stop Deltas (pit_crew_delta) ---")
    pit_deltas = {}
    if raw_laps is not None and len(raw_laps) > 0:
        pit_deltas = compute_pit_deltas(raw_laps)
        for team, delta in sorted(pit_deltas.items(), key=lambda x: x[1]):
            print(f"  {team:15s}: +{delta:.2f}s/stop")
    else:
        print("  No raw lap data available for pit analysis")
    
    # 3. Tire wear factors
    print("\n--- Tire Wear Factors (tire_wear_factor) ---")
    wear_factors = compute_tire_wear_factors(clean_laps)
    for team, factor in sorted(wear_factors.items(), key=lambda x: x[1]):
        print(f"  {team:15s}: {factor:.3f}x")
    
    # Step 4: Update teams.json
    print("\n" + "=" * 60)
    print("  UPDATING teams.json")
    print("=" * 60)
    
    with open(TEAMS_JSON_PATH) as f:
        teams = json.load(f)
    
    updated_count = 0
    for team_id, data in teams.items():
        changes = []
        if team_id in pace_gaps:
            old = data['base_delta']
            data['base_delta'] = pace_gaps[team_id]
            changes.append(f"pace {old:.1f} -> {pace_gaps[team_id]:.3f}")
        
        if team_id in pit_deltas:
            old = data['pit_crew_delta']
            data['pit_crew_delta'] = pit_deltas[team_id]
            changes.append(f"pit {old:.1f} -> {pit_deltas[team_id]:.2f}")
        
        if team_id in wear_factors:
            old = data['tire_wear_factor']
            data['tire_wear_factor'] = wear_factors[team_id]
            changes.append(f"wear {old:.2f} -> {wear_factors[team_id]:.3f}")
        
        if changes:
            print(f"  {team_id:15s}: {', '.join(changes)}")
            updated_count += 1
        else:
            print(f"  {team_id:15s}: (no data -- keeping estimates)")
    
    with open(TEAMS_JSON_PATH, 'w') as f:
        json.dump(teams, f, indent=2)
    
    print(f"\n  [OK] Updated {updated_count} teams in {TEAMS_JSON_PATH}")
    
    # Step 5: Update testing_data.json
    if testing_json:
        print(f"\n  Saving testing data to {TESTING_DATA_PATH}...")
        with open(TESTING_DATA_PATH, 'w') as f:
            json.dump(testing_json, f, indent=2)
        print(f"  [OK] Testing data saved ({len(testing_json)} sessions)")
    
    # Summary
    print("\n" + "=" * 60)
    print("  CALIBRATION COMPLETE")
    print(f"  Source: {source_used}")
    print(f"  Teams updated: {updated_count}/{len(teams)}")
    pace_ok = "YES" if pace_gaps else "NO"
    pit_ok = "YES" if pit_deltas else "NO"
    tire_ok = "YES" if wear_factors else "NO"
    print(f"  Metrics: pace={pace_ok}, pit={pit_ok}, tire={tire_ok}")
    
    # Note about Cadillac
    if 'cadillac' not in pace_gaps:
        print("\n  Note: Cadillac F1 has no data (new 2026 entry) -- keeping estimates")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
