# PitWall Setup Guide

## Pre-Hackathon Checklist

Run through this checklist **before** you need to demo:

### 1. Get API Keys

- [ ] Sign up for Anthropic API: https://console.anthropic.com/
  - Create account
  - Generate API key
  - Copy key to safe place
  
- [ ] Sign up for OpenWeather API: https://openweathermap.org/api
  - Choose free tier
  - Generate API key
  - Copy key to safe place

### 2. Environment Setup

- [ ] Create `backend/.env` file:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENWEATHER_API_KEY=your-openweather-key-here
```

- [ ] Create `frontend/.env.local` file:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
```

- [ ] Verify installation: `pip list | grep fastapi`
- [ ] Test import: `python -c "import fastapi; import fastf1; print('OK')"`

### 4. Pre-Cache F1 Data (CRITICAL!)

This takes 15-20 minutes. Do NOT skip!

```bash
cd data_prep
python fetch_reference_data.py
```

- [ ] Wait for all 4 races to download
- [ ] Verify cache folder exists: `backend/data/cache/`
- [ ] Cache folder should be ~100-200MB

### 5. Frontend Setup

```bash
cd frontend
npm install
```

- [ ] Verify installation: `npm list recharts`
- [ ] Check Next.js version: `npx next --version`

### 6. Test Backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

- [ ] Open browser to http://localhost:8000/docs
- [ ] Test health endpoint: http://localhost:8000/health
- [ ] Should see `{"status":"ok"}`

### 7. Test Frontend

```bash
cd frontend
npm run dev
```

- [ ] Open browser to http://localhost:3000
- [ ] Should see PitWall interface
- [ ] Try selecting a track - dropdown should populate

### 8. Test End-to-End

- [ ] Keep backend running (terminal 1)
- [ ] Keep frontend running (terminal 2)
- [ ] In browser:
  - Select Bahrain
  - Starting compound: SOFT
  - Rain: 0%
  - Safety Car: 20%
  - Click "Optimize Strategy"
- [ ] Wait 20-30 seconds
- [ ] Should see 3 strategies + AI brief

### 9. Troubleshooting

If optimization fails:

1. Check backend terminal for errors
2. Verify API keys in `.env` are correct
3. Test Claude API manually:
```bash
cd backend
python -c "import anthropic; client = anthropic.Anthropic(); print('OK')"
```

If frontend won't connect:

1. Check backend is running on port 8000
2. Check `frontend/.env.local` has correct URL
3. Open browser dev tools → Network tab → look for failed requests

## Quick Start Commands

Terminal 1 (Backend):
```bash
cd backend
venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

Browser:
```
http://localhost:3000
```

## Performance Optimization

If optimization is too slow:

1. Reduce Monte Carlo simulations:
   - Edit `backend/engine/monte_carlo.py`
   - Change `N_SIMULATIONS = 500` to `N_SIMULATIONS = 200`

2. Increase search step size:
   - Edit `backend/engine/optimizer.py`
   - Line 48: `range(10, total - 10, 2)` → `range(10, total - 10, 3)`
   - Line 54: `range(10, total - 20, 3)` → `range(10, total - 20, 4)`

## Known Issues

1. **First optimization is slower**: FastF1 loads data into memory. Subsequent runs are faster.

2. **Claude API rate limits**: Free tier has limits. If you get rate limit errors, wait 60 seconds.

3. **FastF1 cache warnings**: You may see deprecation warnings. These are safe to ignore.

## Success Criteria

You're ready when:
- ✅ Backend starts without errors
- ✅ Frontend loads at localhost:3000
- ✅ Can complete one full optimization in < 30 seconds
- ✅ AI brief generates (not fallback text)
- ✅ Charts render with data
