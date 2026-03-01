# 🏁 PitWall - Quick Start Guide

## What You Have

✅ **Complete F1 Strategy Optimizer** - Fully built, ready to run!

## What You Need

### Required (Cannot skip)
1. **Anthropic API Key** - Get free at https://console.anthropic.com/
2. **OpenWeather API Key** - Get free at https://openweathermap.org/api
3. **Python 3.9+** - Check: `python --version`
4. **Node.js 18+** - Check: `node --version`

### Time Required
- API key signup: 5 minutes
- Backend setup: 10 minutes
- Data caching: 15-20 minutes (one-time)
- Frontend setup: 5 minutes
- **Total: ~40 minutes**

## Step-by-Step Setup

### Step 1: Get API Keys (5 min)

**Anthropic (Claude AI):**
1. Visit https://console.anthropic.com/
2. Create account (use email)
3. Go to "API Keys"
4. Click "Create Key"
5. Copy the key (starts with `sk-ant-`)

**OpenWeather:**
1. Visit https://openweathermap.org/api
2. Sign up for free account
3. Go to "API keys" tab
4. Copy your API key

### Step 2: Configure Environment (1 min)

Create `backend/.env` file:
```env
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENWEATHER_API_KEY=your-openweather-key-here
```

Create `frontend/.env.local` file:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Step 3: Backend Setup (10 min)

Open Terminal 1:
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Wait for all packages to install (~5 min on good internet).

### Step 4: Cache F1 Data (20 min) - CRITICAL!

**Do NOT skip this!** Without cached data, optimization will be very slow.

```bash
cd data_prep
python fetch_reference_data.py
```

You'll see:
```
Fetching 2024 Bahrain...
  ✓ 1234 laps loaded and cached
Fetching 2024 Spain...
  ✓ 1567 laps loaded and cached
...
```

This downloads ~200MB of F1 telemetry data. **Get coffee, this takes 15-20 minutes.**

### Step 5: Frontend Setup (5 min)

Open Terminal 2:
```bash
cd frontend

# Install dependencies
npm install
```

Wait for packages to install (~3 min).

### Step 6: Start Backend (1 min)

In Terminal 1:
```bash
cd backend
venv\Scripts\activate  # If not already activated
uvicorn main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**Test:** Open browser to http://localhost:8000/docs

### Step 7: Start Frontend (1 min)

In Terminal 2:
```bash
cd frontend
npm run dev
```

You should see:
```
ready - started server on 0.0.0.0:3000
```

**Open:** http://localhost:3000

### Step 8: Run First Optimization (30 sec)

1. Select **Bahrain** from dropdown
2. Starting compound: **SOFT**
3. Rain: **0%**
4. Safety car: **20%**
5. Click **"Optimize Strategy"**

Wait 25-30 seconds. You should see:
- ✅ AI brief appears
- ✅ 3 strategies in comparison table
- ✅ Strategy chart renders
- ✅ Robustness metrics show

## ✅ Success Checklist

You're ready to demo when:
- [ ] Backend starts without errors
- [ ] Frontend loads at localhost:3000
- [ ] Track dropdown shows 5 tracks
- [ ] First optimization completes in < 35 seconds
- [ ] AI brief generates (not "Optimal strategy: pit...")
- [ ] Charts render with data
- [ ] Can change settings and re-optimize

## 🚀 Using Batch Scripts (Windows Only)

Double-click these files:
- `setup-data.bat` - Runs data caching
- `start-backend.bat` - Starts backend
- `start-frontend.bat` - Starts frontend

## 🔧 Troubleshooting

### Backend won't start
```bash
# Check Python version
python --version  # Should be 3.9+

# Check if venv is activated
# Should see (venv) in prompt

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### "ANTHROPIC_API_KEY not found"
- Check `backend/.env` exists
- Check API key is correct (starts with sk-ant-)
- Check no extra spaces in .env file

### Frontend can't connect
- Check backend is running (Terminal 1)
- Check port 8000 in use: `netstat -ano | findstr :8000`
- Check `frontend/.env.local` has correct URL

### Optimization very slow (> 60 sec)
- First run is always slower (FastF1 loading)
- If still slow, reduce simulations:
  - Edit `backend/engine/monte_carlo.py`
  - Change `N_SIMULATIONS = 500` to `200`

### No tracks in dropdown
- Backend not running
- Check browser console (F12) for errors
- Check CORS settings in `backend/main.py`

## 📖 Next Steps

Once running:
1. Read `DEMO_SCRIPT.md` for demo preparation
2. Try different tracks and settings
3. Check `STATUS.md` for full system details
4. See `README.md` for architecture deep-dive

## 🎯 Demo Tips

**For best results:**
1. Run one optimization before demo (warms up cache)
2. Keep both terminals visible during demo
3. Have `DEMO_SCRIPT.md` open as reference
4. Practice the 2-minute flow
5. Know the backup plan if live demo fails

## 🆘 Emergency Help

If completely stuck:
1. Check `STATUS.md` - Known Issues section
2. Check both terminal outputs for error messages
3. Try restarting both servers
4. Check `.env` files have correct format
5. Verify data cache exists: `backend/data/cache/`

## 💡 Pro Tips

- **Warm up before demo**: Run 1-2 optimizations
- **Use Bahrain**: Fastest track to optimize
- **Watch backend logs**: Shows optimization progress
- **Test API directly**: Visit http://localhost:8000/docs
- **Check health**: http://localhost:8000/health should return `{"status":"ok"}`

---

**You're all set! The system is complete and ready to impress.** 🏎️💨
