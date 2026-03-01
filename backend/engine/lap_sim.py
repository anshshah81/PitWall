"""
Lap-by-lap race simulation engine (2026 regulations).

2026 key changes modeled:
  - Fuel limit: ~70kg (was 110kg) → lower burn rate, less fuel mass effect
  - Power unit: 50/50 ICE/electric (350kW MGU-K) → energy harvesting penalty
  - Active aero: adjustable downforce → less variable tire thermal load
  - Compound pace offsets: built into tire_delta (c coefficient)
  - Wet conditions: surface-dependent penalties for mismatched compounds
  - Driver tendencies: tire management, wet skill, consistency, overtaking
"""

from models.schemas import TireCompound, RaceConfig, PitStop
from models.tire import tire_delta, MAX_STINT_LAPS
from typing import List, Optional
import random


# ─── 2026 Fuel Constants ─────────────────────────────────────────────────────
# 70kg fuel limit (was 110kg), lighter cars (~768kg min weight)
FUEL_BURN_RATE_KG = 1.05        # kg per lap (70kg / ~66 avg race laps)
FUEL_LAP_TIME_DELTA = 0.030     # seconds per kg (lighter car → less marginal effect)

# ─── 2026 Energy Management ──────────────────────────────────────────────────
# 50/50 electric power: battery state varies lap-to-lap.
# Some laps require harvesting (lift & coast), others allow full deploy.
# Net effect: ~0.15s average penalty per lap, increasing on worn tires.
ENERGY_HARVEST_BASE = 0.15      # base energy management penalty (seconds/lap)
ENERGY_HARVEST_WEAR = 0.005     # extra penalty per stint lap (less grip → worse recovery)

# ─── Wet Condition Modifiers ─────────────────────────────────────────────────
# When track is WET: dry compounds lose massive grip, wet compounds are optimal
WET_TRACK_DELTA = {
    TireCompound.SOFT:          8.0,    # Slick on wet = aquaplaning, near-undriveable
    TireCompound.MEDIUM:        7.0,    # Slightly better but still terrible
    TireCompound.HARD:          6.5,    # Least bad slick (harder rubber, less aquaplaning)
    TireCompound.INTERMEDIATE:  0.0,    # Designed for wet conditions
    TireCompound.WET:          -0.5,    # Slightly better than inters in heavy rain
}

# When track is DRY: wet compounds overheat and grain
DRY_TRACK_WET_TIRE_DELTA = {
    TireCompound.SOFT:          0.0,    # Normal dry performance
    TireCompound.MEDIUM:        0.0,
    TireCompound.HARD:          0.0,
    TireCompound.INTERMEDIATE:  3.5,    # Graining + overheating
    TireCompound.WET:           7.0,    # Severe overheating, rubber destruction
}

# Rain intensity modifiers (scale the WET_TRACK_DELTA penalties)
INTENSITY_SCALE = {
    "light":    0.6,    # Light drizzle: penalties reduced by 40%
    "moderate": 1.0,    # Standard wet: full penalties
    "heavy":    1.3,    # Torrential: 30% worse for dry tires
}


def simulate_lap(
    lap_number: int,
    compound: TireCompound,
    stint_lap: int,
    fuel_load_kg: float,
    base_lap_time: float,
    tire_wear_factor: float = 1.0,
    is_wet: bool = False,
    rain_intensity: str = "moderate",
    driver_data: Optional[dict] = None,
) -> float:
    """
    Simulate a single lap time in seconds (2026 regulations).
    
    Args:
        lap_number: Race lap number
        compound: Current tire compound
        stint_lap: Lap number within current stint (1-indexed)
        fuel_load_kg: Current fuel load in kg
        base_lap_time: Baseline lap time in seconds
        tire_wear_factor: Multiplier for tire degradation (1.0 = baseline)
        is_wet: Whether the track surface is wet on this lap
        rain_intensity: "light", "moderate", or "heavy"
        driver_data: Optional driver tendency dict with keys:
            pace_delta, tire_management, wet_skill, consistency, overtaking_delta
    
    Returns:
        Lap time in seconds
    """
    # ── Driver tendencies (defaults to neutral if no driver selected) ────
    d_pace = 0.0
    d_tire_mgmt = 1.0
    d_wet_skill = 1.0
    d_consistency = 1.0
    d_overtaking = 0.0
    
    if driver_data:
        d_pace = driver_data.get("pace_delta", 0.0)
        d_tire_mgmt = driver_data.get("tire_management", 1.0)
        d_wet_skill = driver_data.get("wet_skill", 1.0)
        d_consistency = driver_data.get("consistency", 1.0)
        d_overtaking = driver_data.get("overtaking_delta", 0.0)
    
    # Tire degradation + compound pace offset (c < 0 for softs/mediums)
    # Driver tire management: <1.0 = gentle (less deg), >1.0 = aggressive (more deg)
    effective_tire_wear = tire_wear_factor * d_tire_mgmt
    deg_delta = tire_delta(compound, stint_lap) * effective_tire_wear
    
    # Fuel mass correction: remaining fuel adds weight penalty
    fuel_delta = fuel_load_kg * FUEL_LAP_TIME_DELTA
    
    # Energy management: 350kW MGU-K harvesting cost, worsens on worn tires
    energy_delta = ENERGY_HARVEST_BASE + ENERGY_HARVEST_WEAR * stint_lap
    
    # Surface condition: compound vs track surface mismatch
    # Driver wet skill scales the wet penalty: <1.0 = less penalty in rain
    intensity_scale = INTENSITY_SCALE.get(rain_intensity, 1.0)
    if is_wet:
        condition_delta = WET_TRACK_DELTA[compound] * intensity_scale * d_wet_skill
    else:
        condition_delta = DRY_TRACK_WET_TIRE_DELTA[compound]
    
    # Driver pace delta (raw speed vs teammate baseline)
    # Driver overtaking delta (positive = loses time in traffic situations)
    driver_delta = d_pace + d_overtaking
    
    # Driver consistency: random lap-to-lap variance
    # consistency < 1.0 = metronomic (small variance)
    # consistency > 1.0 = erratic (large variance)
    consistency_delta = random.gauss(0, 0.15 * d_consistency)
    
    return (base_lap_time + deg_delta + fuel_delta + energy_delta
            + condition_delta + driver_delta + consistency_delta)


def simulate_strategy(
    config: RaceConfig,
    stops: List[PitStop],
    base_lap_time: float,
    pit_loss_seconds: float,
    safety_car_laps: List[int] = None,
    rain_laps: List[int] = None,
    rain_intensity: str = "moderate",
    tire_wear_factor: float = 1.0,
    driver_data: Optional[dict] = None,
) -> float:
    """
    Simulate total race time for a given pit stop strategy.
    
    Args:
        config: Race configuration
        stops: List of pit stops (lap and compound)
        base_lap_time: Baseline lap time for the track
        pit_loss_seconds: Time lost per pit stop
        safety_car_laps: List of laps under safety car (optional)
        rain_laps: List of laps where track is wet (optional)
        rain_intensity: Rain intensity level ("light"/"moderate"/"heavy")
        tire_wear_factor: Multiplier for tire degradation (team-specific)
        driver_data: Optional driver tendency dict
    
    Returns:
        Total race time in seconds
    """
    safety_car_laps = safety_car_laps or []
    rain_laps_set = set(rain_laps or [])
    
    total_time = 0.0
    fuel_load = config.fuel_load_kg
    
    # Build stint sequence from stops
    # Stints: [(start_lap, end_lap, compound), ...]
    pit_laps = [0] + [s.lap for s in stops] + [config.total_laps]
    compounds = [config.starting_compound] + [s.compound for s in stops]
    
    stints = []
    for i in range(len(compounds)):
        start_lap = pit_laps[i] + 1
        end_lap = pit_laps[i + 1]
        stints.append((start_lap, end_lap, compounds[i]))
    
    # Simulate each stint
    for start_lap, end_lap, compound in stints:
        stint_lap = 1
        for lap in range(start_lap, end_lap + 1):
            # Burn fuel
            fuel_load = max(0, fuel_load - FUEL_BURN_RATE_KG)
            
            # Safety car: fixed slow lap time, no tire degradation accrual
            if lap in safety_car_laps:
                total_time += base_lap_time + 25.0  # SC delta ~25s slower
            else:
                is_wet = lap in rain_laps_set
                total_time += simulate_lap(
                    lap, compound, stint_lap, fuel_load, base_lap_time,
                    tire_wear_factor=tire_wear_factor,
                    is_wet=is_wet,
                    rain_intensity=rain_intensity,
                    driver_data=driver_data,
                )
                stint_lap += 1
        
        # Add pit stop time loss (except after last stint)
        if end_lap < config.total_laps:
            total_time += pit_loss_seconds
    
    return total_time
