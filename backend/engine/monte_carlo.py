"""
Monte Carlo robustness scorer.

Runs N simulations with randomized:
  - Safety car events (per-sim probability)
  - Rain events (EXACT matching percentage of sims are wet)

The rain model ensures that if rain_probability = 0.30, exactly 30%
of simulations will have rain. Each rainy sim gets a randomized rain
event (start lap, duration) scaled by the track's rain_intensity.
"""

import random
import numpy as np
from models.schemas import RaceConfig, PitStop, Strategy
from engine.lap_sim import simulate_strategy
from engine.optimizer import _TRACKS, get_team_adjustments
from typing import List, Tuple, Optional


N_SIMULATIONS = 500


# Rain event duration ranges by intensity
RAIN_DURATION = {
    "light":    (5, 12),     # Light drizzle: short bursts
    "moderate": (8, 20),     # Standard rain: medium window
    "heavy":    (15, 30),    # Torrential: long wet period
}


def inject_safety_car(total_laps: int, probability: float) -> List[int]:
    """
    Return list of safety car laps based on probability.
    
    Args:
        total_laps: Total race laps
        probability: Probability of safety car (0.0-1.0)
    
    Returns:
        List of lap numbers under safety car
    """
    sc_laps = []
    if random.random() < probability:
        # Safety car appears somewhere in the middle of the race
        sc_start = random.randint(5, total_laps - 10)
        sc_duration = random.randint(3, 6)
        sc_laps = list(range(sc_start, min(sc_start + sc_duration, total_laps)))
    return sc_laps


def generate_rain_event(total_laps: int, intensity: str = "moderate") -> List[int]:
    """
    Generate a rain event with random timing and duration.
    
    Duration is scaled by rain intensity (tropical tracks get longer rain).
    
    Args:
        total_laps: Total race laps
        intensity: "light", "moderate", or "heavy"
    
    Returns:
        List of lap numbers where track is wet
    """
    min_dur, max_dur = RAIN_DURATION.get(intensity, RAIN_DURATION["moderate"])
    
    # Clamp max duration to available laps
    max_dur = min(max_dur, total_laps - 1)
    min_dur = min(min_dur, max_dur)
    
    # Random start and duration
    rain_duration = random.randint(min_dur, max(min_dur, max_dur))
    rain_start = random.randint(1, max(1, total_laps - rain_duration))
    
    return list(range(rain_start, rain_start + rain_duration))


def score_strategy(
    config: RaceConfig,
    stops: List[PitStop],
    team_data: Optional[dict] = None,
    driver_data: Optional[dict] = None,
    n: int = N_SIMULATIONS,
) -> Tuple[float, float, float, float]:
    """
    Run N Monte Carlo simulations.
    
    EXACT rain matching: if rain_probability = 0.30, then exactly
    round(N * 0.30) simulations will have rain conditions. The rest are dry.
    
    Args:
        config: Race configuration
        stops: Strategy pit stops
        team_data: Optional team metadata for team-specific adjustments
        driver_data: Optional driver tendency dict for driver-specific adjustments
        n: Number of simulations to run
    
    Returns:
        (mean_time, p50_time, p90_time, robustness_score)
    """
    track_data = _TRACKS.get(config.track, {})
    base_time = track_data.get("base_lap_time", 90.0)
    pit_loss = track_data.get("pit_loss", 22.0)
    rain_intensity = track_data.get("rain_intensity", "moderate")
    
    # Apply team-specific adjustments
    base_delta, pit_crew_delta, tire_wear_factor = get_team_adjustments(team_data)
    base_time += base_delta
    pit_loss += pit_crew_delta
    
    # Apply driver pace delta to base time
    if driver_data:
        base_time += driver_data.get("pace_delta", 0.0)
    
    # ── EXACT rain matching ───────────────────────────────────────────────
    # Exactly this many sims will have rain (not probabilistic per-sim)
    n_rainy = round(n * config.rain_probability)
    
    times = []
    for i in range(n):
        # Safety car: probabilistic per-sim (as before)
        sc_laps = inject_safety_car(config.total_laps, config.safety_car_probability)
        
        # Rain: first n_rainy sims are wet, rest are dry
        # (order doesn't matter since we compute statistics over all sims)
        if i < n_rainy:
            rain_laps = generate_rain_event(config.total_laps, rain_intensity)
        else:
            rain_laps = []
        
        t = simulate_strategy(
            config, stops, base_time, pit_loss, sc_laps,
            rain_laps=rain_laps,
            rain_intensity=rain_intensity,
            tire_wear_factor=tire_wear_factor,
            driver_data=driver_data,
        )
        times.append(t)
    
    times = np.array(times)
    mean_time = float(np.mean(times))
    p50 = float(np.percentile(times, 50))
    p90 = float(np.percentile(times, 90))
    
    # Robustness score: based on standard deviation
    # Lower std_dev = higher robustness
    # A std_dev of 0 means perfect robustness (100/100)
    # A std_dev of 60+ means very variable (0/100)
    std_dev = float(np.std(times))
    robustness = max(0.0, min(100.0, 100.0 * (1.0 - std_dev / 60.0)))
    
    return mean_time, p50, p90, round(robustness, 1)


def _fmt_stops(stops: List[PitStop]) -> str:
    """Format pit stops for logging."""
    return ", ".join(f"L{s.lap}->{s.compound.value}" for s in stops)


def _fmt_time(seconds: float) -> str:
    """Format seconds as MM:SS.S"""
    mins = int(seconds // 60)
    secs = seconds % 60
    return f"{mins}:{secs:04.1f}"


def score_top_strategies(
    config: RaceConfig,
    candidates: list,
    team_data: Optional[dict] = None,
    driver_data: Optional[dict] = None,
) -> List[Strategy]:
    """
    Score top candidate strategies and return top 20 Strategy objects.
    
    Two strategies are tagged:
      - OPTIMAL: best P50 time (fastest in ideal conditions)
      - VARIABLE: best robustness score (most consistent under uncertainty)
    
    Args:
        config: Race configuration
        candidates: List of (stops, deterministic_time) tuples from optimizer
        team_data: Optional team metadata for team-specific adjustments
    
    Returns:
        List of up to 20 Strategy objects, sorted by p50 time, with tags
    """
    n_rainy = round(N_SIMULATIONS * config.rain_probability)
    n_to_score = min(len(candidates), 20)
    print(f"    === MONTE CARLO SCORING ({N_SIMULATIONS} sims, {n_rainy} rainy, {n_to_score} candidates) ===")
    
    scored = []
    for idx, (stops, det_time) in enumerate(candidates[:n_to_score], 1):
        mean_t, p50, p90, rob = score_strategy(config, stops, team_data=team_data, driver_data=driver_data)
        scored.append(Strategy(
            stops=stops,
            total_race_time_seconds=round(mean_t, 3),
            robustness_score=rob,
            p50_time=round(p50, 3),
            p90_time=round(p90, 3),
        ))
        stops_str = _fmt_stops(stops)
        print(f"      #{idx:2d}  {stops_str}")
        print(f"           Mean={_fmt_time(mean_t)}  P50={_fmt_time(p50)}  P90={_fmt_time(p90)}  Rob={rob}/100")
    
    # Sort by p50 time (most likely race time under uncertainty)
    scored.sort(key=lambda s: s.p50_time)
    
    # ── Tag the two best strategies ──────────────────────────────────────
    # OPTIMAL = best P50 (fastest in ideal conditions) — always index 0 after sort
    best_optimal_idx = 0
    
    # VARIABLE = highest robustness score (most consistent under uncertainty)
    best_variable_idx = max(range(len(scored)), key=lambda i: scored[i].robustness_score)
    
    scored[best_optimal_idx].tag = "OPTIMAL"
    # Only tag VARIABLE if it's a different strategy
    if best_variable_idx != best_optimal_idx:
        scored[best_variable_idx].tag = "VARIABLE"
    else:
        # If the same strategy is both optimal AND most robust, tag it OPTIMAL
        # and find the second-most-robust for VARIABLE
        if len(scored) > 1:
            remaining = [i for i in range(len(scored)) if i != best_optimal_idx]
            second_best = max(remaining, key=lambda i: scored[i].robustness_score)
            scored[second_best].tag = "VARIABLE"
    
    print(f"    === FINAL TOP 20 (sorted by P50) ===")
    for rank, s in enumerate(scored, 1):
        tag_label = f" <-- {s.tag}" if s.tag else ""
        print(f"      #{rank:2d}  {_fmt_stops(s.stops)}  P50={_fmt_time(s.p50_time)}  Rob={s.robustness_score}/100{tag_label}")
    
    return scored
