"""
AI Race Engineer using Claude API.
Generates F1 team radio style strategy briefs, tailored to specific drivers.
"""

import anthropic
import os
from models.schemas import Strategy, RaceConfig
from typing import Optional, List


def _describe_driver_traits(driver_traits: dict) -> str:
    """Convert driver trait numbers into natural language for Claude."""
    parts = []
    name = driver_traits.get("name", "the driver")
    
    # Tire management (range: 0.83 = elite, 1.10 = poor)
    tm = driver_traits.get("tire_management", 1.0)
    if tm <= 0.85:
        parts.append("legendary tire management — can extend stints 5+ laps beyond expected window")
    elif tm <= 0.91:
        parts.append("excellent tire management — regularly makes tires last longer than rivals")
    elif tm <= 0.95:
        parts.append("good tire management")
    elif tm <= 1.0:
        parts.append("average tire management")
    elif tm > 1.03:
        parts.append("hard on tires — tends to overdrive, expect shorter stints or graining")
    
    # Wet skill (range: 0.76 = best ever, 0.96 = poor)
    ws = driver_traits.get("wet_skill", 1.0)
    if ws <= 0.80:
        parts.append("one of the greatest wet-weather drivers in F1 history")
    elif ws <= 0.87:
        parts.append("exceptional in the wet — rain is an advantage")
    elif ws <= 0.92:
        parts.append("strong in wet conditions")
    elif ws <= 0.95:
        parts.append("capable in the wet")
    elif ws > 0.95:
        parts.append("less comfortable in wet conditions — be cautious")
    
    # Consistency (range: 0.84 = metronomic, 1.14 = erratic)
    con = driver_traits.get("consistency", 1.0)
    if con <= 0.87:
        parts.append("metronomic consistency — almost never makes unforced errors")
    elif con <= 0.92:
        parts.append("very consistent lap-to-lap")
    elif con <= 0.97:
        parts.append("generally consistent")
    elif con > 1.05:
        parts.append("lap times can be variable — high peaks but less predictable, watch for errors")
    
    # Overtaking (range: -0.18 = best, +0.06 = stuck in traffic)
    ov = driver_traits.get("overtaking_delta", 0.0)
    if ov <= -0.13:
        parts.append("elite overtaker — decisive late-braking moves, dominates wheel-to-wheel")
    elif ov <= -0.08:
        parts.append("strong aggressive overtaker")
    elif ov <= -0.04:
        parts.append("good overtaking ability")
    elif ov <= 0.0:
        parts.append("average in traffic")
    elif ov > 0.03:
        parts.append("struggles to overtake — prefers track position from qualifying, may get stuck behind slower cars")
    
    # Include driver notes if available (gives Claude historical context)
    notes = driver_traits.get("notes", "")
    if notes:
        parts.append(f"Background: {notes}")
    
    return "; ".join(parts) if parts else "well-rounded driver profile"


def generate_brief(
    strategy: Strategy,
    config: RaceConfig,
    team_name: Optional[str] = None,
    drivers: Optional[List[str]] = None,
    selected_driver: Optional[str] = None,
    driver_traits: Optional[dict] = None,
) -> str:
    """
    Generate a race engineer strategy brief using Claude.
    
    Args:
        strategy: Optimal strategy with pit stops
        config: Race configuration
        team_name: Optional team name for team-specific briefs
        drivers: Optional list of driver names (2026 roster)
        selected_driver: Name of the specific driver being optimized for
        driver_traits: Optional dict with driver tendency values
    
    Returns:
        Brief string (2-3 sentences in F1 team radio style)
    """
    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key == "your_anthropic_key_here":
        return generate_fallback_brief(strategy, config, team_name, drivers, selected_driver, driver_traits)
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        # Format pit stops for prompt
        stops_text = ", ".join([
            f"Lap {s.lap} → {s.compound.value}"
            for s in strategy.stops
        ])
        
        # Convert race time to minutes:seconds
        total_mins = int(strategy.total_race_time_seconds // 60)
        total_secs = strategy.total_race_time_seconds % 60
        
        team_context = ""
        if team_name:
            team_context = f"\n- Team: {team_name}"
        
        # ── Driver-specific context ─────────────────────────────────────
        driver_context = ""
        if selected_driver:
            driver_context = f"\n- Driver: {selected_driver}"
            if driver_traits:
                traits_desc = _describe_driver_traits(driver_traits)
                driver_context += f"\n- Driver profile: {traits_desc}"
        
        driver_instruction = ""
        if selected_driver:
            first_name = selected_driver.split()[0]
            driver_instruction = f"""

CRITICAL: Address this brief DIRECTLY to {selected_driver} (use "{first_name}").
This is a 2026 season brief. The strategy has been specifically optimized for {selected_driver}'s driving characteristics.
If this driver is known for tire management, mention extending stints.
If this driver is strong in the wet, mention that rain could be an advantage.
Keep it personal and driver-aware — reference their strengths tactically."""
        elif drivers and all(d != "TBA" for d in drivers):
            driver_instruction = f"""

CRITICAL DRIVER INFORMATION — 2026 SEASON ROSTER:
The ONLY drivers for {team_name} in the 2026 season are: {drivers[0]} and {drivers[1]}.
You MUST address the brief to either "{drivers[0]}" or "{drivers[1]}" by first name.
Do NOT use any other driver names. The 2026 roster has changed from previous seasons."""
        
        prompt = f"""You are a Formula 1 race engineer for the 2026 season. Generate a concise, confident race strategy brief — 
the kind you would deliver to a driver on the formation lap over team radio.

Race config:
- Track: {config.track.upper()}
- Total laps: {config.total_laps}
- Starting compound: {config.starting_compound.value}
- Rain probability: {config.rain_probability * 100:.0f}%{team_context}{driver_context}

Optimal strategy:
- Pit stops: {stops_text}
- Expected race time: {total_mins}m {total_secs:.1f}s
- Robustness score: {strategy.robustness_score}/100

Write 2-3 sentences maximum. Be direct and tactical. Use the language a real F1 engineer would use.
No preamble. Start with the key message. Reference lap numbers and compounds.{driver_instruction}"""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return message.content[0].text
    
    except Exception as e:
        print(f"Warning: Claude API failed: {e}")
        return generate_fallback_brief(strategy, config, team_name, drivers, selected_driver, driver_traits)


def generate_fallback_brief(
    strategy: Strategy,
    config: RaceConfig,
    team_name: Optional[str] = None,
    drivers: Optional[List[str]] = None,
    selected_driver: Optional[str] = None,
    driver_traits: Optional[dict] = None,
) -> str:
    """
    Generate a simple fallback brief if Claude API is unavailable.
    """
    stops_text = ", ".join([
        f"lap {s.lap} to {s.compound.value}s"
        for s in strategy.stops
    ])
    
    team_prefix = f"[{team_name}] " if team_name else ""
    driver_ref = ""
    if selected_driver:
        driver_ref = f"{selected_driver}, "
    elif drivers and all(d != "TBA" for d in drivers):
        driver_ref = f"{drivers[0].split()[0]}, "
    
    trait_hint = ""
    if driver_traits:
        tm = driver_traits.get("tire_management", 1.0)
        if tm <= 0.90:
            trait_hint = " Your tire management gives us flexibility to push the stints."
        elif tm > 1.03:
            trait_hint = " Keep the tires alive, manage your inputs."
    
    return f"{team_prefix}{driver_ref}Optimal strategy: pit {stops_text}. Robustness {strategy.robustness_score}/100.{trait_hint} Execute the plan."
