# PitWall - 2 Minute Demo Script

## Setup Before Demo

1. ✅ Backend running on port 8000
2. ✅ Frontend running on localhost:3000
3. ✅ Browser at localhost:3000
4. ✅ Have run at least one optimization (to warm up FastF1 cache)

## Demo Flow (2 minutes)

### Opening (15 seconds)

> "This is **PitWall** - an F1 race strategy optimizer that answers the question every team faces: when should I pit, and which tires should I use?"

> "It combines real F1 telemetry data, Monte Carlo simulation, and AI to generate optimal pit strategies in seconds."

### Part 1: Basic Optimization (30 seconds)

**Action:** Configure race
- Track: **Bahrain**
- Starting compound: **SOFT**
- Rain probability: **0%**
- Safety car probability: **20%**

**While configuring, say:**
> "We're simulating the Bahrain GP - 57 laps, starting on soft tires, with a 20% chance of safety car."

**Click "Optimize Strategy"**

**While waiting (~25 seconds), say:**
> "Behind the scenes, PitWall is:"
> - "Running a dynamic programming optimizer over thousands of pit window combinations"
> - "Simulating each lap with physics-based tire degradation and fuel effects"
> - "Then running 500 Monte Carlo simulations with randomized safety car events"
> - "Finally, Claude AI generates a race engineer style brief"

### Part 2: Results Analysis (30 seconds)

**When results appear:**

**Point to AI Brief:**
> "Here's the AI brief - it's telling us to pit on lap 18 for mediums. This is what you'd hear on team radio."

**Point to Strategy Comparison:**
> "We get 3 strategies. Strategy 1 is optimal - one stop on lap 18."
> "Notice the **robustness score** - 87 out of 100. This measures how well the strategy performs under uncertainty."

**Point to Chart:**
> "This shows lap-by-lap time delta. The vertical line is our pit stop."

### Part 3: What-If Analysis (30 seconds)

**Action:** Adjust rain probability slider to **60%**

**Say:**
> "Now watch what happens if rain probability increases to 60%."

**Click "Optimize Strategy" again**

**While waiting:**
> "The optimizer is re-running with the new weather conditions..."

**When results appear:**
> "See how the strategy changed? The pit timing and compounds shifted to handle the rain probability."
> "This is real-time strategic decision making."

### Part 4: Robustness Insight (15 seconds)

**Scroll to Robustness Analysis:**

**Say:**
> "This is the key insight: **P50 vs P90 time**."
> "Strategy 1 might be 0.8 seconds faster on average, but Strategy 2 might be more robust under a safety car."
> "That's the difference between a theoretical optimal and a real-world winning strategy."

### Closing (10 seconds)

**Say:**
> "Real F1 teams have rooms full of engineers doing this analysis. **PitWall puts it in a browser.**"

> "Built in 24 hours with FastAPI, FastF1, Claude AI, and Next.js."

## Quick Recovery Lines

If optimization is slow:
> "Monte Carlo simulation with 500 runs takes time - this is the same compute F1 teams use on supercomputers."

If Claude API fails:
> "The AI brief uses Claude's API - we have a fallback if the API is rate limited."

If questions about accuracy:
> "The tire degradation curves are fitted from real 2024 F1 telemetry data via the FastF1 library."

## Key Points to Emphasize

1. **Real F1 Data** - Not simulated, actual telemetry from FastF1
2. **Monte Carlo Robustness** - Not just speed, but reliability under uncertainty
3. **AI Integration** - Claude generates natural language insights
4. **Full Stack** - Backend simulation + Frontend visualization + AI = complete system

## Demo Variations

### If Short on Time (1 minute):
- Skip Part 3 (What-If Analysis)
- Just show one optimization and explain robustness

### If Extra Time (3+ minutes):
- Compare multiple tracks
- Show different starting compounds
- Explain the physics model in detail
- Show the code structure

### If Technical Audience:
- Open backend code (`engine/optimizer.py`)
- Explain dynamic programming approach
- Show Monte Carlo implementation
- Discuss API design decisions

### If Non-Technical Audience:
- Focus on UI/UX
- Emphasize "one click" simplicity
- Compare to what F1 teams actually do
- Show only final results, skip technical details

## Backup Plan

If live demo fails:
1. Have screenshots ready
2. Walk through the workflow document
3. Show the code structure
4. Explain the architecture diagram
