# PitWall Project Structure

```
HackTAMS/
│
├── 📄 README.md                    # Main project documentation
├── 📄 QUICKSTART.md                # 40-minute setup guide
├── 📄 SETUP.md                     # Pre-hackathon checklist
├── 📄 DEMO_SCRIPT.md               # 2-minute demo flow
├── 📄 STATUS.md                    # Project status & specs
├── 📄 ENV_SETUP.md                 # Environment variable guide
├── 📄 BUILD_COMPLETE.md            # Final build summary
├── 📄 .gitignore                   # Git ignore rules
│
├── 🔧 start-backend.bat            # Windows: Start backend
├── 🔧 start-frontend.bat           # Windows: Start frontend
├── 🔧 setup-data.bat               # Windows: Cache F1 data
│
├── 📁 backend/                     # Python FastAPI Backend
│   │
│   ├── 📄 main.py                  # FastAPI entry point (3 endpoints)
│   ├── 📄 requirements.txt         # Python dependencies
│   ├── 📄 ENV_TEMPLATE.md          # .env file template
│   ├── 📄 .env                     # ⚠️ CREATE THIS (API keys)
│   │
│   ├── 📁 models/                  # Data models
│   │   ├── __init__.py
│   │   ├── schemas.py              # Pydantic models (API contracts)
│   │   └── tire.py                 # Tire degradation physics
│   │
│   ├── 📁 engine/                  # Core optimization engine
│   │   ├── __init__.py
│   │   ├── lap_sim.py              # Lap-by-lap simulator
│   │   ├── optimizer.py            # Strategy optimizer (DP)
│   │   └── monte_carlo.py          # Robustness scorer (500 sims)
│   │
│   ├── 📁 ai/                      # AI integration
│   │   ├── __init__.py
│   │   └── race_engineer.py        # Claude API (strategy briefs)
│   │
│   └── 📁 data/
│       ├── tracks.json             # 5 track configurations
│       └── cache/                  # FastF1 cache (auto-created)
│
├── 📁 frontend/                    # Next.js React Frontend
│   │
│   ├── 📄 package.json             # Node dependencies
│   ├── 📄 tsconfig.json            # TypeScript config
│   ├── 📄 next.config.js           # Next.js config
│   ├── 📄 tailwind.config.js       # Tailwind CSS + F1 colors
│   ├── 📄 postcss.config.js        # PostCSS config
│   ├── 📄 ENV_TEMPLATE.md          # .env.local template
│   ├── 📄 .env.local               # ⚠️ CREATE THIS (API URL)
│   │
│   ├── 📁 app/                     # Next.js 14 App Router
│   │   ├── layout.tsx              # Root layout
│   │   ├── page.tsx                # Main application page
│   │   └── globals.css             # Global styles
│   │
│   ├── 📁 components/              # React Components
│   │   ├── ConfigPanel.tsx         # Race configuration UI
│   │   ├── AIBrief.tsx            # Team radio display
│   │   ├── StrategyChart.tsx      # Recharts lap visualization
│   │   ├── ComparisonTable.tsx    # 3-strategy comparison
│   │   └── RobustnessChart.tsx    # Monte Carlo metrics
│   │
│   └── 📁 lib/
│       └── api.ts                  # Backend API client
│
└── 📁 data_prep/                   # Data preparation
    └── fetch_reference_data.py    # FastF1 data cacher (run once)
```

## File Counts

| Category | Count |
|----------|-------|
| **Python Files** | 12 |
| **TypeScript/JavaScript** | 11 |
| **Documentation** | 8 |
| **Configuration** | 6 |
| **Batch Scripts** | 3 |
| **Total Files** | 40+ |

## Key Directories

### Backend (`backend/`)
- **Purpose**: REST API server for optimization
- **Tech**: FastAPI, FastF1, NumPy, Claude API
- **Endpoints**: `/health`, `/tracks`, `/optimize`
- **Port**: 8000

### Frontend (`frontend/`)
- **Purpose**: Interactive web UI
- **Tech**: Next.js 14, React, TypeScript, Recharts
- **Components**: 5 main components
- **Port**: 3000

### Data Prep (`data_prep/`)
- **Purpose**: Pre-cache F1 telemetry data
- **Size**: ~200MB cached data
- **Time**: 15-20 minutes (one-time)

## Files You Need to Create

⚠️ These are NOT in the repository (security):

1. **`backend/.env`**
   ```env
   ANTHROPIC_API_KEY=sk-ant-your-key
   OPENWEATHER_API_KEY=your-key
   ```

2. **`frontend/.env.local`**
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

See `ENV_SETUP.md` for detailed instructions.

## Generated at Runtime

These folders/files are created automatically:

- `backend/venv/` - Python virtual environment
- `backend/data/cache/` - FastF1 cache (after running data_prep)
- `frontend/node_modules/` - NPM packages
- `frontend/.next/` - Next.js build output

All are gitignored.

## Import Relationships

```
main.py
├── models.schemas ─────────┐
├── engine.optimizer ───────┤
│   └── engine.lap_sim      │
│       └── models.tire     │
├── engine.monte_carlo      │
│   └── engine.lap_sim ─────┤
└── ai.race_engineer        │
    └── models.schemas ─────┘
```

## Data Flow

```
User (Browser)
    │
    ↓ HTTP Request
frontend/app/page.tsx
    │
    ↓ fetch()
frontend/lib/api.ts
    │
    ↓ POST /optimize
backend/main.py
    │
    ├─→ engine/optimizer.py ──→ engine/lap_sim.py ──→ models/tire.py
    │                                    ↓
    ├─→ engine/monte_carlo.py ──────────┘
    │
    └─→ ai/race_engineer.py ──→ Claude API
    │
    ↓ JSON Response
frontend/components/*.tsx
    │
    ↓ Render
User sees results
```

## Build Order

Following the plan dependency graph:

1. ✅ Backend models (`schemas.py`, `tire.py`)
2. ✅ Engine core (`lap_sim.py`, `optimizer.py`, `monte_carlo.py`)
3. ✅ AI integration (`race_engineer.py`)
4. ✅ FastAPI app (`main.py`)
5. ✅ Frontend setup (`package.json`, configs)
6. ✅ API client (`lib/api.ts`)
7. ✅ React components (`components/*.tsx`)
8. ✅ Main app (`app/page.tsx`)
9. ✅ Documentation (all `.md` files)
10. ✅ Utility scripts (`.bat` files)

## Next Steps

1. **Read**: `QUICKSTART.md` for setup
2. **Create**: `.env` files (see `ENV_SETUP.md`)
3. **Install**: Dependencies (`pip` + `npm`)
4. **Cache**: F1 data (`setup-data.bat`)
5. **Run**: Both servers
6. **Test**: One optimization
7. **Demo**: Use `DEMO_SCRIPT.md`

---

**Project Status: 100% Complete** ✅
