"""
Pydantic data models for PitWall API.
All request/response schemas defined here.
"""

from pydantic import BaseModel
from typing import List, Optional, Dict
from enum import Enum


class TireCompound(str, Enum):
    """F1 tire compound types (2026 regulations)"""
    SOFT = "SOFT"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    INTERMEDIATE = "INTERMEDIATE"
    WET = "WET"


class RaceConfig(BaseModel):
    """User configuration for race optimization"""
    track: str                          # e.g. "bahrain"
    total_laps: int
    starting_compound: TireCompound
    fuel_load_kg: float = 70.0         # 2026 regs: reduced from 110kg to ~70kg
    rain_probability: float = 0.0       # 0.0 to 1.0
    safety_car_probability: float = 0.2
    team: Optional[str] = None          # e.g. "red_bull", None = generic car
    driver: Optional[str] = None        # e.g. "verstappen", None = team average


class PitStop(BaseModel):
    """Single pit stop: lap number and tire compound"""
    lap: int
    compound: TireCompound


class Strategy(BaseModel):
    """Complete race strategy with performance metrics"""
    stops: List[PitStop]
    total_race_time_seconds: float
    robustness_score: float             # 0-100, higher = more robust
    p50_time: float                     # Median race time (Monte Carlo)
    p90_time: float                     # 90th percentile race time
    tag: Optional[str] = None           # "OPTIMAL", "VARIABLE", or None


class DriverInfo(BaseModel):
    """Individual driver characteristics"""
    id: str                             # e.g. "verstappen"
    name: str                           # e.g. "Max Verstappen"
    number: int                         # e.g. 1
    pace_delta: float                   # seconds vs teammate (+ = slower)
    tire_management: float              # multiplier on tire wear (<1 = gentle)
    wet_skill: float                    # multiplier on wet penalty (<1 = rain master)
    consistency: float                  # multiplier on lap time variance (<1 = consistent)
    overtaking_delta: float             # per-lap traffic penalty (negative = strong overtaker)


class TeamInfo(BaseModel):
    """Team metadata returned by /teams endpoint"""
    id: str
    name: str
    short: str
    color: str
    base_delta: float
    pit_crew_delta: float
    tire_wear_factor: float
    drivers: Dict[str, DriverInfo]      # driver_id -> DriverInfo


class OptimizeResponse(BaseModel):
    """API response from /optimize endpoint"""
    strategies: List[Strategy]          # Top 20 strategies (tagged: OPTIMAL, VARIABLE)
    ai_brief: str                       # Claude-generated race brief
    config: RaceConfig                  # Echo back the config
    team_info: Optional[TeamInfo] = None  # Team data if team was selected
    driver_info: Optional[DriverInfo] = None  # Driver data if driver was selected
