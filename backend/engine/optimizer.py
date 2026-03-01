"""
Convergent beam-search strategy optimizer.

Instead of brute-force enumeration, this optimizer:
  1. Seeds extreme/opposite strategies (earliest vs. latest pits, all compound combos)
  2. Evaluates them with a deterministic simulation (including expected rain)
  3. Iteratively refines the top candidates by exploring neighboring pit laps
  4. Converges to the optimal strategy from both directions

This approach is more efficient AND explores the strategy space better
than exhaustive enumeration — it starts wide and narrows down.
"""

from models.schemas import RaceConfig, TireCompound, PitStop, Strategy
from models.tire import MAX_STINT_LAPS
from engine.lap_sim import simulate_strategy
from typing import List, Optional, Set, Tuple
import json


# ─── Track Data ───────────────────────────────────────────────────────────────
_TRACKS = {}
try:
    with open("data/tracks.json") as f:
        _TRACKS = json.load(f)
except FileNotFoundError:
    print("Warning: data/tracks.json not found in optimizer. Using defaults.")


# ─── Beam Search Parameters ──────────────────────────────────────────────────
BEAM_WIDTH = 30          # Top strategies kept at each refinement step
MIN_STINT_LAPS = 8       # Minimum laps per stint (below this, pit loss outweighs benefit)
REFINEMENT_STEPS = [4, 2, 1]  # Progressively finer search (lap offsets)


# ─── Compound Sets ───────────────────────────────────────────────────────────
DRY_COMPOUNDS = [TireCompound.SOFT, TireCompound.MEDIUM, TireCompound.HARD]
WET_COMPOUNDS = [TireCompound.INTERMEDIATE, TireCompound.WET]
ALL_COMPOUNDS = DRY_COMPOUNDS + WET_COMPOUNDS


def get_available_compounds(config: RaceConfig) -> List[TireCompound]:
    """
    Determine which compounds are available based on rain probability.
    
    - rain < 0.20  → dry only (SOFT, MEDIUM, HARD)
    - rain 0.20-0.5 → dry + intermediate (changeable conditions)
    - rain > 0.5   → all compounds including full wet
    """
    if config.rain_probability < 0.20:
        return DRY_COMPOUNDS
    elif config.rain_probability < 0.5:
        return DRY_COMPOUNDS + [TireCompound.INTERMEDIATE]
    else:
        return ALL_COMPOUNDS


def expected_rain_laps(total_laps: int, rain_probability: float) -> List[int]:
    """
    Generate expected rain laps for deterministic evaluation.
    
    Uses rain_probability to estimate how much of the race is wet.
    Places rain in the middle portion of the race (most strategically impactful).
    
    Args:
        total_laps: Total race laps
        rain_probability: 0.0-1.0 probability of rain
    
    Returns:
        List of lap numbers expected to be wet
    """
    if rain_probability < 0.05:
        return []
    
    # Expected wet laps: proportional to rain probability
    # At 50% rain prob, ~25% of laps are wet (rain doesn't cover entire race)
    wet_fraction = rain_probability * 0.5
    n_wet = max(3, int(total_laps * wet_fraction))
    
    # Center rain in middle third of race (most strategic impact)
    mid = total_laps // 2
    start = max(1, mid - n_wet // 2)
    end = min(total_laps, start + n_wet)
    return list(range(start, end + 1))


def _strategy_key(stops: List[PitStop]) -> Tuple:
    """Hashable key for deduplication."""
    return tuple((s.lap, s.compound.value) for s in stops)


def _fmt_strategy(stops: List[PitStop], time: float = None) -> str:
    """Format a strategy as a readable string for logging."""
    parts = [f"L{s.lap}->{s.compound.value}" for s in stops]
    label = f"{len(stops)}-stop: {', '.join(parts)}"
    if time is not None:
        mins = int(time // 60)
        secs = time % 60
        label += f"  ({mins}:{secs:05.2f})"
    return label


def _is_valid_strategy(stops: List[PitStop], total_laps: int) -> bool:
    """Check that a strategy has valid lap ordering and spacing."""
    laps = [s.lap for s in stops]
    # All pit laps within bounds
    if any(l < MIN_STINT_LAPS or l > total_laps - MIN_STINT_LAPS for l in laps):
        return False
    # Monotonically increasing
    if laps != sorted(laps):
        return False
    # Minimum spacing between stops
    for i in range(len(laps) - 1):
        if laps[i + 1] - laps[i] < MIN_STINT_LAPS:
            return False
    return True


def generate_extreme_seeds(config: RaceConfig) -> List[List[PitStop]]:
    """
    Generate seed strategies from extreme/opposite positions.
    
    Covers the full strategy space by placing pit stops at wide-spread
    positions: very early, early, midpoint, late, very late.
    Both 1-stop and 2-stop strategies are seeded.
    
    This is the "start in opposite directions" part — we begin with
    the most diverse possible set of strategies before converging.
    """
    compounds = get_available_compounds(config)
    total = config.total_laps
    seeds: List[List[PitStop]] = []
    seen: Set[Tuple] = set()
    
    def add_if_valid(stops: List[PitStop]):
        if not _is_valid_strategy(stops, total):
            return
        key = _strategy_key(stops)
        if key not in seen:
            seen.add(key)
            seeds.append(stops)
    
    # ── 1-Stop Seeds ──────────────────────────────────────────────────────
    # Spread across race distance: 15% to 85% in 6 positions
    pct_1stop = [0.15, 0.25, 0.35, 0.50, 0.65, 0.75, 0.85]
    for pct in pct_1stop:
        pit_lap = int(total * pct)
        for c in compounds:
            if c != config.starting_compound:
                add_if_valid([PitStop(lap=pit_lap, compound=c)])
    
    # ── 2-Stop Seeds ─────────────────────────────────────────────────────
    # Combinations of early/mid/late for each stop (covers opposite extremes)
    pct_2stop = [0.18, 0.30, 0.42, 0.55, 0.68, 0.80]
    for i, p1_pct in enumerate(pct_2stop[:-1]):
        for p2_pct in pct_2stop[i + 1:]:
            p1 = int(total * p1_pct)
            p2 = int(total * p2_pct)
            for c1 in compounds:
                for c2 in compounds:
                    add_if_valid([
                        PitStop(lap=p1, compound=c1),
                        PitStop(lap=p2, compound=c2),
                    ])
    
    return seeds


def generate_neighbors(
    top_strategies: List[Tuple[List[PitStop], float]],
    step: int,
    total_laps: int,
    existing_keys: Set[Tuple],
) -> List[List[PitStop]]:
    """
    Generate neighbor strategies by shifting each pit stop ±step laps.
    
    Only produces strategies not already in the existing set (deduplication).
    
    Args:
        top_strategies: Current best (stops, time) tuples
        step: Lap offset to try (e.g. ±4, ±2, ±1)
        total_laps: Total race laps (for bounds checking)
        existing_keys: Set of already-evaluated strategy keys
    
    Returns:
        List of new neighbor strategies to evaluate
    """
    neighbors: List[List[PitStop]] = []
    
    for stops, _ in top_strategies:
        for i in range(len(stops)):
            for offset in [-step, step]:
                new_lap = stops[i].lap + offset
                # Create modified strategy
                new_stops = list(stops)
                new_stops[i] = PitStop(lap=new_lap, compound=stops[i].compound)
                
                if not _is_valid_strategy(new_stops, total_laps):
                    continue
                
                key = _strategy_key(new_stops)
                if key not in existing_keys:
                    existing_keys.add(key)
                    neighbors.append(new_stops)
    
    return neighbors


def get_team_adjustments(team_data: Optional[dict]) -> tuple:
    """
    Get team-specific performance adjustments.
    
    Args:
        team_data: Team metadata dict from teams.json, or None for generic car
    
    Returns:
        (base_delta, pit_crew_delta, tire_wear_factor)
    """
    if team_data is None:
        return (0.0, 0.0, 1.0)
    
    return (
        team_data.get("base_delta", 0.0),
        team_data.get("pit_crew_delta", 0.0),
        team_data.get("tire_wear_factor", 1.0),
    )


def _run_beam_search(
    config: RaceConfig,
    base_time: float,
    pit_loss: float,
    rain_intensity: str,
    rain_laps: List[int],
    tire_wear_factor: float,
    pass_label: str = "",
    driver_data: Optional[dict] = None,
) -> List[Tuple[List[PitStop], float]]:
    """
    Single beam-search pass: seed extremes → refine → return sorted results.
    """
    prefix = f"      [{pass_label}] " if pass_label else "      "

    def evaluate(strategies: List[List[PitStop]]) -> List[Tuple[List[PitStop], float]]:
        results = []
        for stops in strategies:
            t = simulate_strategy(
                config, stops, base_time, pit_loss,
                rain_laps=rain_laps,
                rain_intensity=rain_intensity,
                tire_wear_factor=tire_wear_factor,
                driver_data=driver_data,
            )
            results.append((stops, t))
        return results
    
    seeds = generate_extreme_seeds(config)
    all_keys = {_strategy_key(s) for s in seeds}
    
    results = evaluate(seeds)
    results.sort(key=lambda x: x[1])
    
    print(f"{prefix}Seeds: {len(seeds)} strategies, best = {_fmt_strategy(results[0][0], results[0][1])}")
    
    for step in REFINEMENT_STEPS:
        top = results[:BEAM_WIDTH]
        neighbors = generate_neighbors(top, step, config.total_laps, all_keys)
        if neighbors:
            neighbor_results = evaluate(neighbors)
            combined = results + neighbor_results
            combined.sort(key=lambda x: x[1])
            results = combined
        print(f"{prefix}Refine +/-{step}: +{len(neighbors)} new -> best = {_fmt_strategy(results[0][0], results[0][1])}")
    
    # Log top 5 from this pass
    print(f"{prefix}Top 5 from this pass:")
    for rank, (stops, t) in enumerate(results[:5], 1):
        print(f"{prefix}  #{rank}  {_fmt_strategy(stops, t)}")
    
    return results


def optimize(config: RaceConfig, team_data: Optional[dict] = None, driver_data: Optional[dict] = None) -> List[tuple]:
    """
    Dual-pass convergent beam-search optimizer.
    
    When rain > 0, runs TWO independent passes:
      1. DRY pass: evaluates strategies assuming no rain
      2. WET pass: evaluates strategies with expected rain laps
    Then merges top 5 from each and sends 10 to Monte Carlo.
    
    Monte Carlo's exact rain-percentage matching determines the true winner.
    This prevents the deterministic pass from over-fitting to either condition.
    
    Args:
        config: Race configuration
        team_data: Optional team metadata dict for team-specific adjustments
        driver_data: Optional driver tendency dict for driver-specific adjustments
    
    Returns:
        List of (stops, total_time) tuples, sorted by total_time
    """
    track_data = _TRACKS.get(config.track, {})
    base_time = track_data.get("base_lap_time", 90.0)
    pit_loss = track_data.get("pit_loss", 22.0)
    rain_intensity = track_data.get("rain_intensity", "moderate")
    
    # Apply team-specific adjustments
    base_delta, pit_crew_delta, tire_wear_factor = get_team_adjustments(team_data)
    base_time += base_delta
    pit_loss += pit_crew_delta
    
    # Apply driver pace delta to base time (driver-specific raw speed)
    if driver_data:
        base_time += driver_data.get("pace_delta", 0.0)
    
    if config.rain_probability < 0.05:
        # ── Pure dry: single pass, no rain ────────────────────────────────
        print("    Single pass (dry)")
        results = _run_beam_search(
            config, base_time, pit_loss, rain_intensity,
            rain_laps=[], tire_wear_factor=tire_wear_factor,
            pass_label="DRY",
            driver_data=driver_data,
        )
        top = results[:20]
        print(f"    === TOP {len(top)} CANDIDATES FOR MONTE CARLO ===")
        for rank, (stops, t) in enumerate(top, 1):
            print(f"      #{rank:2d}  {_fmt_strategy(stops, t)}")
        return top
    
    # ── Dual pass: dry + wet ──────────────────────────────────────────────
    # Pass 1: Evaluate as if fully dry (favors dry compound strategies)
    print("    Pass 1 (dry evaluation)...")
    dry_results = _run_beam_search(
        config, base_time, pit_loss, rain_intensity,
        rain_laps=[], tire_wear_factor=tire_wear_factor,
        pass_label="DRY",
        driver_data=driver_data,
    )
    
    # Pass 2: Evaluate with expected rain (favors wet compound strategies)
    det_rain_laps = expected_rain_laps(config.total_laps, config.rain_probability)
    print(f"    Pass 2 (wet evaluation, {len(det_rain_laps)} expected rain laps)...")
    wet_results = _run_beam_search(
        config, base_time, pit_loss, rain_intensity,
        rain_laps=det_rain_laps, tire_wear_factor=tire_wear_factor,
        pass_label="WET",
        driver_data=driver_data,
    )
    
    # ── Merge: top 10 from each pass, deduplicated (→ up to 20) ────────
    seen: Set[Tuple] = set()
    merged: List[Tuple[List[PitStop], float]] = []
    
    for results_pool in [dry_results, wet_results]:
        count = 0
        for stops, t in results_pool:
            key = _strategy_key(stops)
            if key not in seen:
                seen.add(key)
                merged.append((stops, t))
                count += 1
                if count >= 10:
                    break
    
    # Sort merged candidates by deterministic time (best estimate)
    merged.sort(key=lambda x: x[1])
    
    top = merged[:20]
    print(f"    === MERGED {len(top)} CANDIDATES FOR MONTE CARLO ===")
    for rank, (stops, t) in enumerate(top, 1):
        print(f"      #{rank:2d}  {_fmt_strategy(stops, t)}")
    
    return top
