"""
Tire degradation model for F1 compounds.
Calibrated for 2026 regulations:
  - Active aerodynamics → reduced thermal stress → ~25-30% less overall degradation
  - 50/50 electric power (350kW MGU-K) → smoother torque → less rear tire stress
  - Lighter cars (~768kg vs 798kg) → less energy through tires
  - Compound pace offsets (c coefficient) model the REAL advantage of softer rubber
    so the optimizer properly trades grip vs. longevity.
"""

import numpy as np
from models.schemas import TireCompound


# ─── 2026 Degradation Model ─────────────────────────────────────────────────
#
# time_delta = a * stint_lap^2 + b * stint_lap + c
#
# c < 0 → compound is FASTER than baseline (softer rubber grip advantage)
# c = 0 → baseline compound (hard)
#
# Key insight: without the c offset, the optimizer has NO reason to ever
# choose softs/mediums — they just degrade faster with no upside.
# With offsets, softs gain ~0.8s/lap early but cross over to slower after ~13 laps.
#
DEGRADATION_COEFFS = {
    TireCompound.SOFT:         (0.0012, 0.060, -0.80),   # Fast grip, crossover ~lap 13
    TireCompound.MEDIUM:       (0.0006, 0.032, -0.40),   # Balanced, crossover ~lap 12
    TireCompound.HARD:         (0.0003, 0.018,  0.00),   # Durable baseline
    TireCompound.INTERMEDIATE: (0.0008, 0.035, -0.30),   # Wet-dry transition
    TireCompound.WET:          (0.0005, 0.025, -0.20),   # Full wet, good in heavy rain
}


# Maximum viable stint length per compound
# 2026: active aero keeps tires in thermal window longer → extended stint viability
MAX_STINT_LAPS = {
    TireCompound.SOFT:         28,    # Was 25 (2024)
    TireCompound.MEDIUM:       40,    # Was 35
    TireCompound.HARD:         50,    # Was 45
    TireCompound.INTERMEDIATE: 35,    # Grooved, moderate life
    TireCompound.WET:          30,    # Full wets, short window of use
}


# Cliff parameters: after CLIFF_THRESHOLD % of max stint, degradation spikes
CLIFF_THRESHOLD = 0.80    # cliff kicks in at 80% of max stint
CLIFF_EXPONENT = 2.5      # how aggressively the cliff punishes (exponential)
CLIFF_SCALE = 0.15        # base multiplier for cliff penalty


def tire_delta(compound: TireCompound, stint_lap: int) -> float:
    """
    Returns lap time delta in seconds due to tire degradation at given stint lap.
    
    Includes a "tire cliff" effect: after ~80% of the compound's max stint life,
    degradation spikes exponentially — modeling the real phenomenon where tires
    fall off a cliff in performance when pushed too far.
    
    Args:
        compound: Tire compound type
        stint_lap: Lap number within the stint (1-indexed)
    
    Returns:
        Time delta in seconds (negative = faster than baseline, positive = slower)
    """
    a, b, c = DEGRADATION_COEFFS[compound]
    base_delta = a * stint_lap**2 + b * stint_lap + c
    
    # Tire cliff: exponential penalty when exceeding threshold of max stint
    max_laps = MAX_STINT_LAPS[compound]
    cliff_start = int(max_laps * CLIFF_THRESHOLD)
    
    if stint_lap > cliff_start:
        laps_past_cliff = stint_lap - cliff_start
        cliff_penalty = CLIFF_SCALE * (laps_past_cliff ** CLIFF_EXPONENT)
        base_delta += cliff_penalty
    
    return base_delta


def fit_degradation_from_fastf1(laps_df, compound: str) -> tuple:
    """
    Fit degradation polynomial from real FastF1 data.
    Call this in data_prep to generate real coefficients.
    
    Args:
        laps_df: FastF1 laps DataFrame filtered to compound and clean laps
        compound: Compound name as string (e.g., 'SOFT')
    
    Returns:
        (a, b, c) coefficients for quadratic fit
    """
    compound_laps = laps_df[
        (laps_df['Compound'] == compound) & 
        (laps_df['LapTime'].notna()) &
        (laps_df['PitInTime'].isna()) &  # Not in-lap
        (laps_df['PitOutTime'].isna())    # Not out-lap
    ].copy()
    
    if len(compound_laps) == 0:
        print(f"Warning: No clean laps found for {compound}")
        return (0.0, 0.0, 0.0)
    
    stint_laps = compound_laps['TyreLife'].values
    # Convert LapTime (timedelta) to seconds
    lap_times = compound_laps['LapTime'].dt.total_seconds().values
    
    # Normalize: subtract median base lap time
    base_time = np.median(lap_times[stint_laps <= 5])
    deltas = lap_times - base_time
    
    # Fit quadratic polynomial
    coeffs = np.polyfit(stint_laps, deltas, 2)
    return tuple(coeffs)
