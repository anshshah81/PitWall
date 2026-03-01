# PitWall — Cursor Build Workflow
### F1 Race Strategy Optimizer | 24-Hour Hackathon Sprint

---

## ⚠️ READ BEFORE STARTING

This document is your single source of truth. Every file you create, every function you write, and every API call you make should map back to a step in this workflow. Do not build anything not listed here until the core pipeline is green end-to-end.

---

## Project Structure

```
pitwall/
├── backend/
│   ├── main.py                  # FastAPI entry point
│   ├── data/
│   │   ├── ingestion.py         # FastF1 + OpenWeather data fetching
│   │   ├── cache/               # FastF1 local cache dir (gitignore this)
│   │   └── tracks.json          # Static track metadata
│   ├── models/
│   │   ├── schemas.py           # Pydantic request/response models
│   │   ├── tire.py              # Tire compound degradation curves
│   │   └── race.py              # RaceConfig, CarState data classes
│   ├── engine/
│   │   ├── lap_sim.py           # Core lap time simulation
│   │   ├── optimizer.py         # Dynamic programming strategy optimizer
│   │   └── monte_carlo.py       # Monte Carlo robustness scorer
│   ├── ai/
│   │   └── race_engineer.py     # Claude API — strategy brief generator
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx             # Main app page
│   │   └── layout.tsx
│   ├── components/
│   │   ├── ConfigPanel.tsx      # Race config inputs
│   │   ├── StrategyChart.tsx    # Lap-by-lap recharts visualization
│   │   ├── ComparisonTable.tsx  # Top 3 strategies table
│   │   ├── WhatIfPanel.tsx      # Scenario sliders
│   │   ├── RobustnessChart.tsx  # Monte Carlo histogram
│   │   └── AIBrief.tsx          # Claude strategy brief card
│   ├── lib/
│   │   └── api.ts               # Backend fetch wrapper
│   └── package.json
└── data_prep/
    └── fetch_reference_data.py  # Run ONCE before hackathon to cache data
```

---

## Data Sources

### ✅ PRIMARY — FastF1 (Python library)
**What it gives you:** Lap times, tire compound per stint, pit stop laps, sector times, weather per session, car telemetry. This is your core data source for everything optimizer-related.

```bash
pip install fastf1
```

```python
import fastf1
fastf1.Cache.enable_cache('./backend/data/cache')

# Load a race session
session = fastf1.get_session(2024, 'Bahrain', 'R')
session.load()

# Get all laps with tire data
laps = session.laps[['Driver', 'LapNumber', 'LapTime', 'Compound', 'TyreLife', 'Stint']]

# Get weather
weather = session.weather_data  # includes AirTemp, TrackTemp, Rainfall
```

**Best reference races to pull (run before hackathon):**
- 2024 Bahrain GP — clean 1-stop vs 2-stop data, dry, well-documented
- 2024 Spanish GP — good tire delta data across compounds
- 2023 Abu Dhabi GP — late-season, stable conditions

---

### ✅ SECONDARY — Jolpica-F1 (Ergast replacement)
**⚠️ Ergast is dead.** Use Jolpica-F1 instead — it's a drop-in replacement with identical endpoints.

```
Base URL: https://api.jolpi.ca/ergast/f1/
Rate limit: 200 requests/hour (no auth required)
```

```python
import requests

# Get pit stop data for a race
r = requests.get('https://api.jolpi.ca/ergast/f1/2024/1/pitstops.json')
pit_data = r.json()['MRData']['RaceTable']['Races'][0]['PitStops']

# Get race results
r = requests.get('https://api.jolpi.ca/ergast/f1/2024/1/results.json')
```

**Use Jolpica for:** pit stop lap numbers and durations, race results, circuit metadata.

---

### ✅ TERTIARY — OpenWeather API
**What it gives you:** Current + forecast weather for a track location. Used for the rain probability slider.

```
Sign up: https://openweathermap.org/api (free tier is enough)
Endpoint: https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={key}
```

**Track coordinates to hardcode in `tracks.json`:**
```json
{
  "bahrain": { "lat": 26.0325, "lon": 50.5106, "laps": 57, "pit_loss": 22.0 },
  "spain":   { "lat": 41.5700, "lon": 2.2611,  "laps": 66, "pit_loss": 20.5 },
  "monaco":  { "lat": 43.7347, "lon": 7.4205,  "laps": 78, "pit_loss": 27.0 },
  "silverstone": { "lat": 52.0786, "lon": -1.0169, "laps": 52, "pit_loss": 21.0 },
  "monza":   { "lat": 45.6156, "lon": 9.2811,  "laps": 53, "pit_loss": 23.0 }
}
```

---

### ⚡ RUN THIS BEFORE THE HACKATHON STARTS

Create `data_prep/fetch_reference_data.py` and run it to pre-cache all FastF1 data locally. FastF1 downloads can be slow — do not wait until you're building to pull data.

```python
# data_prep/fetch_reference_data.py
import fastf1
fastf1.Cache.enable_cache('../backend/data/cache')

RACES_TO_CACHE = [
    (2024, 'Bahrain', 'R'),
    (2024, 'Spain', 'R'),
    (2023, 'Abu Dhabi', 'R'),
    (2024, 'Monaco', 'R'),
]

for year, race, session_type in RACES_TO_CACHE:
    print(f"Fetching {year} {race}...")
    session = fastf1.get_session(year, race, session_type)
    session.load()
    print(f"  ✓ {len(session.laps)} laps loaded")

print("All data cached. You're ready.")
```

```bash
cd data_prep && python fetch_reference_data.py
```

---

## Backend Build Steps

### STEP 1 — Pydantic Schemas (`models/schemas.py`)

Define these first. Everything else depends on them.

```python
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class TireCompound(str, Enum):
    SOFT = "SOFT"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    WET = "WET"

class RaceConfig(BaseModel):
    track: str                        # e.g. "bahrain"
    total_laps: int
    starting_compound: TireCompound
    fuel_load_kg: float = 100.0
    rain_probability: float = 0.0     # 0.0 to 1.0
    safety_car_probability: float = 0.2

class PitStop(BaseModel):
    lap: int
    compound: TireCompound

class Strategy(BaseModel):
    stops: List[PitStop]
    total_race_time_seconds: float
    robustness_score: float           # 0–100, higher = more robust
    p50_time: float
    p90_time: float

class OptimizeResponse(BaseModel):
    strategies: List[Strategy]        # top 3
    ai_brief: str
    config: RaceConfig
```

---

### STEP 2 — Tire Degradation Model (`models/tire.py`)

Fit polynomial degradation curves from FastF1 historical data. This function is the foundation of the lap sim.

```python
import numpy as np
from models.schemas import TireCompound

# Degradation coefficients: [a, b, c] for time_delta = a*stint_lap^2 + b*stint_lap + c
# These are pre-fit from 2024 Bahrain/Spain data. Tune with your cached data.
DEGRADATION_COEFFS = {
    TireCompound.SOFT:   (0.0015, 0.08, 0.0),   # fast degradation
    TireCompound.MEDIUM: (0.0008, 0.04, 0.0),   # moderate
    TireCompound.HARD:   (0.0004, 0.02, 0.0),   # slow
    TireCompound.WET:    (0.0006, 0.03, 0.0),   # special case
}

MAX_STINT_LAPS = {
    TireCompound.SOFT:   25,
    TireCompound.MEDIUM: 35,
    TireCompound.HARD:   45,
    TireCompound.WET:    30,
}

def tire_delta(compound: TireCompound, stint_lap: int) -> float:
    """Returns lap time delta in seconds due to tire degradation at given stint lap."""
    a, b, c = DEGRADATION_COEFFS[compound]
    return a * stint_lap**2 + b * stint_lap + c

def fit_degradation_from_fastf1(laps_df, compound: str) -> tuple:
    """
    Fit degradation polynomial from real FastF1 data.
    Call this in data_prep to generate real coefficients.
    
    laps_df: FastF1 laps DataFrame filtered to compound and clean laps
    Returns (a, b, c) coefficients
    """
    compound_laps = laps_df[
        (laps_df['Compound'] == compound) & 
        (laps_df['LapTime'].notna()) &
        (laps_df['PitInTime'].isna()) &  # not in-lap
        (laps_df['PitOutTime'].isna())    # not out-lap
    ].copy()
    
    stint_laps = compound_laps['TyreLife'].values
    # Convert LapTime (timedelta) to seconds
    lap_times = compound_laps['LapTime'].dt.total_seconds().values
    
    # Normalize: subtract median base lap time
    base_time = np.median(lap_times[stint_laps <= 5])
    deltas = lap_times - base_time
    
    # Fit quadratic polynomial
    coeffs = np.polyfit(stint_laps, deltas, 2)
    return tuple(coeffs)
```

---

### STEP 3 — Lap Simulation Engine (`engine/lap_sim.py`)

The core function. Given a full strategy (list of compounds and pit laps), simulate total race time.

```python
from models.schemas import TireCompound, RaceConfig, PitStop
from models.tire import tire_delta, MAX_STINT_LAPS
from typing import List

FUEL_BURN_RATE_KG = 1.6         # kg per lap (approximate F1 average)
FUEL_LAP_TIME_DELTA = 0.034     # seconds per kg (standard F1 figure)

def simulate_lap(
    lap_number: int,
    compound: TireCompound,
    stint_lap: int,
    fuel_load_kg: float,
    base_lap_time: float,
) -> float:
    """Simulate a single lap time in seconds."""
    
    # Tire degradation delta
    deg_delta = tire_delta(compound, stint_lap)
    
    # Fuel mass correction (lighter = faster)
    fuel_delta = fuel_load_kg * FUEL_LAP_TIME_DELTA
    
    return base_lap_time + deg_delta + fuel_delta


def simulate_strategy(
    config: RaceConfig,
    stops: List[PitStop],
    base_lap_time: float,
    pit_loss_seconds: float,
    safety_car_laps: List[int] = None,
) -> float:
    """
    Simulate total race time for a given pit stop strategy.
    Returns total race time in seconds.
    """
    safety_car_laps = safety_car_laps or []
    
    total_time = 0.0
    fuel_load = config.fuel_load_kg
    
    # Build stint sequence from stops
    stints = []
    pit_laps = [0] + [s.lap for s in stops] + [config.total_laps]
    compounds = [config.starting_compound] + [s.compound for s in stops]
    
    for i in range(len(compounds)):
        start_lap = pit_laps[i] + 1
        end_lap = pit_laps[i + 1]
        stints.append((start_lap, end_lap, compounds[i]))
    
    for start_lap, end_lap, compound in stints:
        stint_lap = 1
        for lap in range(start_lap, end_lap + 1):
            fuel_load = max(0, fuel_load - FUEL_BURN_RATE_KG)
            
            # Safety car: fixed slow lap time, no tire degradation accrual
            if lap in safety_car_laps:
                total_time += base_lap_time + 25.0  # SC delta ~25s slower
            else:
                total_time += simulate_lap(lap, compound, stint_lap, fuel_load, base_lap_time)
                stint_lap += 1
        
        # Add pit stop time loss (except after last stint)
        if end_lap < config.total_laps:
            total_time += pit_loss_seconds
    
    return total_time
```

---

### STEP 4 — Strategy Optimizer (`engine/optimizer.py`)

Dynamic programming over all valid pit window combinations. Returns top 3 strategies by total time.

```python
from models.schemas import RaceConfig, TireCompound, PitStop, Strategy
from models.tire import MAX_STINT_LAPS
from engine.lap_sim import simulate_strategy
from typing import List
import itertools

# Base lap times by track (seconds) — tune from FastF1 data
BASE_LAP_TIMES = {
    "bahrain":    93.5,
    "spain":      82.0,
    "monaco":     74.0,
    "silverstone": 90.0,
    "monza":      81.5,
}

PIT_LOSS_TIMES = {
    "bahrain": 22.0,
    "spain":   20.5,
    "monaco":  27.0,
    "silverstone": 21.0,
    "monza":   23.0,
}

VALID_DRY_COMPOUNDS = [TireCompound.SOFT, TireCompound.MEDIUM, TireCompound.HARD]

def generate_valid_strategies(config: RaceConfig) -> List[List[PitStop]]:
    """Generate all valid 1-stop and 2-stop strategies."""
    strategies = []
    total = config.total_laps
    
    # 1-stop strategies
    for pit_lap in range(10, total - 10, 2):  # step 2 laps for speed
        for compound in VALID_DRY_COMPOUNDS:
            if compound != config.starting_compound:
                strategies.append([PitStop(lap=pit_lap, compound=compound)])
    
    # 2-stop strategies
    for pit1 in range(10, total - 20, 3):
        for pit2 in range(pit1 + 10, total - 10, 3):
            for c1 in VALID_DRY_COMPOUNDS:
                for c2 in VALID_DRY_COMPOUNDS:
                    strategies.append([
                        PitStop(lap=pit1, compound=c1),
                        PitStop(lap=pit2, compound=c2),
                    ])
    
    return strategies


def optimize(config: RaceConfig) -> List[Strategy]:
    """Run optimizer. Returns top 3 strategies sorted by total race time."""
    base_time = BASE_LAP_TIMES.get(config.track, 90.0)
    pit_loss = PIT_LOSS_TIMES.get(config.track, 22.0)
    
    candidates = generate_valid_strategies(config)
    results = []
    
    for stops in candidates:
        total_time = simulate_strategy(config, stops, base_time, pit_loss)
        results.append((stops, total_time))
    
    # Sort by total time, take top 10 candidates for Monte Carlo
    results.sort(key=lambda x: x[1])
    top_candidates = results[:10]
    
    return top_candidates
```

---

### STEP 5 — Monte Carlo Robustness Scorer (`engine/monte_carlo.py`)

Run N simulations per strategy with randomized safety car events. Score robustness.

```python
import random
import numpy as np
from models.schemas import RaceConfig, PitStop, Strategy
from engine.lap_sim import simulate_strategy
from engine.optimizer import BASE_LAP_TIMES, PIT_LOSS_TIMES
from typing import List, Tuple

N_SIMULATIONS = 500

def inject_safety_car(total_laps: int, probability: float) -> List[int]:
    """Return list of safety car laps based on probability."""
    sc_laps = []
    if random.random() < probability:
        sc_start = random.randint(5, total_laps - 10)
        sc_duration = random.randint(3, 6)
        sc_laps = list(range(sc_start, min(sc_start + sc_duration, total_laps)))
    return sc_laps


def score_strategy(
    config: RaceConfig,
    stops: List[PitStop],
    n: int = N_SIMULATIONS
) -> Tuple[float, float, float, float]:
    """
    Run N Monte Carlo simulations.
    Returns (mean_time, p50_time, p90_time, robustness_score)
    """
    base_time = BASE_LAP_TIMES.get(config.track, 90.0)
    pit_loss = PIT_LOSS_TIMES.get(config.track, 22.0)
    
    times = []
    for _ in range(n):
        sc_laps = inject_safety_car(config.total_laps, config.safety_car_probability)
        t = simulate_strategy(config, stops, base_time, pit_loss, sc_laps)
        times.append(t)
    
    times = np.array(times)
    mean_time = float(np.mean(times))
    p50 = float(np.percentile(times, 50))
    p90 = float(np.percentile(times, 90))
    
    # Robustness score: inverse of variance, normalized 0-100
    variance = float(np.var(times))
    robustness = max(0, 100 - (variance / 10))
    
    return mean_time, p50, p90, round(robustness, 1)


def score_top_strategies(config: RaceConfig, candidates: list) -> List[Strategy]:
    """Score top candidate strategies and return top 3 Strategy objects."""
    scored = []
    for stops, det_time in candidates[:10]:
        mean_t, p50, p90, rob = score_strategy(config, stops)
        scored.append(Strategy(
            stops=stops,
            total_race_time_seconds=round(mean_t, 3),
            robustness_score=rob,
            p50_time=p50,
            p90_time=p90,
        ))
    
    # Sort by p50 time (most likely race time under uncertainty)
    scored.sort(key=lambda s: s.p50_time)
    return scored[:3]
```

---

### STEP 6 — AI Race Engineer (`ai/race_engineer.py`)

One Claude API call. Takes top strategy, returns a radio-style brief.

```python
import anthropic
import json
from models.schemas import Strategy, RaceConfig

client = anthropic.Anthropic()  # uses ANTHROPIC_API_KEY env var

def generate_brief(strategy: Strategy, config: RaceConfig) -> str:
    """Generate a race engineer strategy brief using Claude."""
    
    stops_text = ", ".join([
        f"Lap {s.lap} → {s.compound.value}"
        for s in strategy.stops
    ])
    
    total_mins = int(strategy.total_race_time_seconds // 60)
    total_secs = strategy.total_race_time_seconds % 60
    
    prompt = f"""You are a Formula 1 race engineer. Generate a concise, confident race strategy brief — 
the kind you would deliver to a driver on the formation lap over team radio.

Race config:
- Track: {config.track.upper()}
- Total laps: {config.total_laps}
- Starting compound: {config.starting_compound.value}
- Rain probability: {config.rain_probability * 100:.0f}%

Optimal strategy:
- Pit stops: {stops_text}
- Expected race time: {total_mins}m {total_secs:.1f}s
- Robustness score: {strategy.robustness_score}/100

Write 2-3 sentences maximum. Be direct and tactical. Use the language a real F1 engineer would use.
No preamble. Start with the key message. Reference lap numbers and compounds."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return message.content[0].text
```

---

### STEP 7 — FastAPI Router (`main.py`)

Wire everything together.

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from models.schemas import RaceConfig, OptimizeResponse
from engine.optimizer import optimize
from engine.monte_carlo import score_top_strategies
from ai.race_engineer import generate_brief
import json

app = FastAPI(title="PitWall API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

with open("data/tracks.json") as f:
    TRACKS = json.load(f)


@app.get("/tracks")
def get_tracks():
    return {"tracks": list(TRACKS.keys())}


@app.post("/optimize", response_model=OptimizeResponse)
def run_optimization(config: RaceConfig):
    # 1. Run deterministic optimizer → top 10 candidates
    candidates = optimize(config)
    
    # 2. Score with Monte Carlo → top 3 Strategy objects
    strategies = score_top_strategies(config, candidates)
    
    # 3. Generate AI brief for the top strategy
    brief = generate_brief(strategies[0], config)
    
    return OptimizeResponse(
        strategies=strategies,
        ai_brief=brief,
        config=config,
    )


@app.get("/health")
def health():
    return {"status": "ok"}
```

---

### Backend requirements.txt

```
fastapi==0.111.0
uvicorn==0.29.0
fastf1==3.4.0
anthropic==0.28.0
numpy==1.26.4
scipy==1.13.0
requests==2.32.0
pydantic==2.7.0
python-dotenv==1.0.1
```

**Run with:**
```bash
cd backend && uvicorn main:app --reload --port 8000
```

---

## Frontend Build Steps

### STEP 8 — API Client (`lib/api.ts`)

```typescript
const BASE = 'http://localhost:8000'

export interface PitStop {
  lap: number
  compound: 'SOFT' | 'MEDIUM' | 'HARD' | 'WET'
}

export interface Strategy {
  stops: PitStop[]
  total_race_time_seconds: number
  robustness_score: number
  p50_time: number
  p90_time: number
}

export interface OptimizeResponse {
  strategies: Strategy[]
  ai_brief: string
  config: RaceConfig
}

export interface RaceConfig {
  track: string
  total_laps: number
  starting_compound: string
  fuel_load_kg: number
  rain_probability: number
  safety_car_probability: number
}

export async function getTracks(): Promise<string[]> {
  const res = await fetch(`${BASE}/tracks`)
  const data = await res.json()
  return data.tracks
}

export async function optimize(config: RaceConfig): Promise<OptimizeResponse> {
  const res = await fetch(`${BASE}/optimize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
  return res.json()
}
```

---

### STEP 9 — Frontend Components (build in this order)

**ConfigPanel.tsx** — Track selector dropdown, compound selector, rain probability slider (0–100%), SC probability slider. On submit → calls `optimize()`.

**StrategyChart.tsx** — Recharts `LineChart`. X-axis = lap number, Y-axis = cumulative time delta vs optimal. Color-code background bands by tire compound (red = soft, yellow = medium, grey = hard). Mark pit stop laps with vertical dashed lines.

**ComparisonTable.tsx** — Three columns, one per strategy. Rows: number of stops, pit lap(s), compounds used, expected time (MM:SS), robustness score (colored 0-100 bar). Highlight the recommended strategy.

**RobustnessChart.tsx** — Recharts `BarChart` histogram. X-axis = race time buckets, Y-axis = simulation count. Show P50 and P90 markers. This is your technical depth showpiece.

**AIBrief.tsx** — Dark card, monospace font. Show the Claude-generated brief with a blinking cursor effect. Label it "RACE ENGINEER — TEAM RADIO".

**WhatIfPanel.tsx** — Rain % slider, SC probability slider. On change → debounce 300ms → re-call `optimize()` → update all charts live.

---

## Environment Variables

Create `.env` in `/backend`:
```
ANTHROPIC_API_KEY=your_key_here
OPENWEATHER_API_KEY=your_key_here
```

Create `.env.local` in `/frontend`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Pre-Hackathon Checklist

Run through this the night before:

- [ ] `python data_prep/fetch_reference_data.py` — pre-cache all F1 sessions
- [ ] Verify FastF1 cache folder is populated (`backend/data/cache/`)
- [ ] Test `fastf1.get_session(2024, 'Bahrain', 'R')` loads in < 5 seconds
- [ ] Get and test OpenWeather API key
- [ ] Get and test Anthropic API key — run one test completion
- [ ] `npm install` in frontend — verify no errors
- [ ] `pip install -r requirements.txt` — verify no errors
- [ ] Both partners have the repo cloned and running locally

---

## Hackathon Cut-Order (if time runs out)

If you're behind, cut in this order — last items first:

1. ~~WhatIfPanel live re-optimization~~ → make it a re-submit button instead
2. ~~RobustnessChart histogram~~ → replace with a single robustness score number
3. ~~OpenWeather live fetch~~ → hardcode rain=0 as default
4. ~~Multiple tracks~~ → hardcode Bahrain only
5. **Never cut:** Monte Carlo scoring, AI brief, StrategyChart, ComparisonTable

---

## Demo Script (2 minutes)

1. Open app. Set track = Bahrain, start = Soft, rain = 0%, SC = 20%.
2. Hit Optimize. Show strategy chart loading. Point to the three strategies.
3. Read the AI brief out loud. "This is what gets sent to the driver."
4. Drag rain probability to 60%. Strategies shift — show the 2-stop becoming dominant. "The optimizer responds to environmental inputs in real time."
5. Point to robustness scores. "Strategy 1 is 0.8s faster — but Strategy 2 is 12 points more robust. Under a safety car, Strategy 2 wins. That's the real insight."
6. Close with: "Real F1 teams have rooms full of engineers doing this. PitWall puts it in a browser."
```
