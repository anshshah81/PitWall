# PitWall - F1 Race Strategy Optimizer

> Formula 1 race strategy optimization powered by AI, Monte Carlo simulation, and real F1 telemetry data.

![PitWall](https://img.shields.io/badge/F1-Strategy%20Optimizer-E10600?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=next.js&logoColor=white)
![Claude](https://img.shields.io/badge/Claude-AI-8A2BE2?style=for-the-badge)

## Overview

PitWall is a real-time Formula 1 race strategy optimization tool that answers: **"When should I pit, and which tires should I use?"**

### Key Features

- 🏎️ **Physics-Based Simulation** - Models tire degradation, fuel effects, and pit stop timing
- 🎲 **Monte Carlo Analysis** - 500 simulations per strategy to measure robustness under uncertainty
- 🤖 **AI Race Engineer** - Claude-powered strategy briefs in F1 team radio style
- 📊 **Interactive Visualization** - Real-time charts and comparison tables
- 📈 **Real F1 Data** - Built on FastF1 historical telemetry data

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Next.js   │ ───▶ │   FastAPI    │ ───▶ │   FastF1    │
│   Frontend  │      │   Backend    │      │    Data     │
└─────────────┘      └──────────────┘      └─────────────┘
                            │
                            ├───▶ Strategy Optimizer
                            ├───▶ Monte Carlo Scorer
                            └───▶ Claude AI (Anthropic)
```

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- Anthropic API key ([Get one here](https://console.anthropic.com/))
- OpenWeather API key ([Get one here](https://openweathermap.org/api))

### 1. Clone and Setup

```bash
git clone <your-repo-url>
cd HackTAMS
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
# Create backend/.env with:
ANTHROPIC_API_KEY=your_key_here
OPENWEATHER_API_KEY=your_key_here
```

### 3. Pre-Cache F1 Data (Important!)

This downloads historical F1 data (~15-20 minutes):

```bash
cd data_prep
python fetch_reference_data.py
```

### 4. Start Backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Backend will be available at `http://localhost:8000`

### 5. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
# Create frontend/.env.local with:
NEXT_PUBLIC_API_URL=http://localhost:8000

# Start dev server
npm run dev
```

Frontend will be available at `http://localhost:3000`

## Usage

1. **Select Track**: Choose from Bahrain, Spain, Monaco, Silverstone, or Monza
2. **Configure Race**: Set starting tire compound, rain probability, safety car probability
3. **Optimize**: Click "Optimize Strategy" and wait 20-30 seconds
4. **Analyze Results**:
   - Top 3 strategies with robustness scores
   - AI-generated race engineer brief
   - Lap-by-lap visualization
   - Monte Carlo robustness analysis

## Project Structure

```
HackTAMS/
├── backend/
│   ├── main.py                  # FastAPI entry point
│   ├── models/
│   │   ├── schemas.py           # Pydantic data models
│   │   └── tire.py              # Tire degradation curves
│   ├── engine/
│   │   ├── lap_sim.py           # Lap time simulator
│   │   ├── optimizer.py         # Strategy optimizer
│   │   └── monte_carlo.py       # Robustness scorer
│   ├── ai/
│   │   └── race_engineer.py     # Claude AI integration
│   └── data/
│       ├── tracks.json          # Track metadata
│       └── cache/               # FastF1 cache (gitignored)
├── frontend/
│   ├── app/
│   │   ├── page.tsx             # Main app page
│   │   └── layout.tsx
│   ├── components/
│   │   ├── ConfigPanel.tsx
│   │   ├── AIBrief.tsx
│   │   ├── StrategyChart.tsx
│   │   ├── ComparisonTable.tsx
│   │   └── RobustnessChart.tsx
│   └── lib/
│       └── api.ts               # Backend API client
└── data_prep/
    └── fetch_reference_data.py  # Data pre-caching script
```

## API Endpoints

### `GET /health`
Health check

### `GET /tracks`
Returns list of available tracks

### `POST /optimize`
Main optimization endpoint

**Request Body:**
```json
{
  "track": "bahrain",
  "total_laps": 57,
  "starting_compound": "SOFT",
  "fuel_load_kg": 100,
  "rain_probability": 0.0,
  "safety_car_probability": 0.2
}
```

**Response:**
```json
{
  "strategies": [
    {
      "stops": [{"lap": 18, "compound": "MEDIUM"}],
      "total_race_time_seconds": 5234.5,
      "robustness_score": 87.3,
      "p50_time": 5235.1,
      "p90_time": 5289.7
    }
  ],
  "ai_brief": "Box lap 18 for mediums...",
  "config": { ... }
}
```

## Technologies

**Backend:**
- FastAPI - High-performance Python web framework
- FastF1 - Official F1 telemetry library
- NumPy/SciPy - Numerical computation
- Anthropic Claude - AI strategy brief generation

**Frontend:**
- Next.js 14 - React framework with App Router
- TypeScript - Type safety
- TailwindCSS - Styling
- Recharts - Data visualization

## Performance

- **Optimization Time**: ~10 seconds (deterministic optimizer)
- **Monte Carlo Scoring**: ~15 seconds (500 simulations)
- **Total Response Time**: ~25-30 seconds
- **Strategy Space**: ~5,000 candidate strategies per race

## Demo Script

For a 2-minute demo:

1. Set **Bahrain**, **SOFT** start, **0% rain**, **20% SC**
2. Click "Optimize" → show 3 strategies + AI brief
3. Adjust rain to **60%** → re-optimize → strategies shift
4. Explain robustness scores: "Strategy 2 is 0.8s slower but 12 points more robust"
5. Close: *"Real F1 teams have rooms full of engineers. PitWall puts it in a browser."*

## Troubleshooting

### Backend won't start
- Verify Python 3.9+ is installed: `python --version`
- Check all dependencies installed: `pip list`
- Ensure `.env` file exists with valid API keys

### Frontend won't connect to backend
- Verify backend is running on port 8000
- Check `frontend/.env.local` has correct API URL
- Check browser console for CORS errors

### Optimization is slow
- Reduce Monte Carlo simulations in `backend/engine/monte_carlo.py` (500 → 200)
- Increase strategy search step size in `optimizer.py`

### FastF1 data not loading
- Run `data_prep/fetch_reference_data.py` first
- Verify `backend/data/cache/` folder exists and is populated
- Check internet connection (FastF1 downloads data on first use)

## Contributing

This project was built for a 24-hour hackathon. Contributions welcome!

## License

MIT License - see LICENSE file

## Acknowledgments

- FastF1 library for F1 telemetry data
- Anthropic Claude for AI insights
- F1 community for inspiration

---

**Built with ❤️ for the racing strategy nerds**
