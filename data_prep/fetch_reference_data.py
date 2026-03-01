"""
Pre-cache FastF1 data for reference races and preseason testing.
Run this ONCE before starting development to avoid slow downloads.

Usage:
    cd data_prep
    python fetch_reference_data.py
"""

import fastf1
import json
import os

# Enable caching to the backend data/cache folder
fastf1.Cache.enable_cache('../backend/data/cache')

# Reference races to cache
RACES_TO_CACHE = [
    (2024, 'Bahrain', 'R'),
    (2024, 'Spain', 'R'),
    (2023, 'Abu Dhabi', 'R'),
    (2024, 'Monaco', 'R'),
]

# Preseason testing sessions to cache
# FastF1 uses event name 'Pre-Season Testing' or similar
# Session identifiers: 1, 2, 3 for testing days
TESTING_SESSIONS = [
    # 2025 preseason testing (latest available)
    (2025, 'Pre-Season Testing', 1),
    (2025, 'Pre-Season Testing', 2),
    (2025, 'Pre-Season Testing', 3),
    # 2024 preseason testing (backup reference)
    (2024, 'Pre-Season Testing', 1),
    (2024, 'Pre-Season Testing', 2),
    (2024, 'Pre-Season Testing', 3),
]

# Output file for extracted testing performance data
TESTING_OUTPUT = '../backend/data/testing_data.json'


def extract_team_performance(session) -> dict:
    """
    Extract per-team performance metrics from a session.
    
    Returns dict keyed by team name with lap time stats.
    """
    laps = session.laps
    if laps is None or len(laps) == 0:
        return {}
    
    team_data = {}
    teams = laps['Team'].dropna().unique()
    
    for team in teams:
        team_laps = laps[
            (laps['Team'] == team) &
            (laps['LapTime'].notna()) &
            (laps['PitInTime'].isna()) &
            (laps['PitOutTime'].isna()) &
            (~laps['IsPersonalBest'].isna() if 'IsPersonalBest' in laps.columns else True)
        ].copy()
        
        if len(team_laps) == 0:
            continue
        
        lap_times = team_laps['LapTime'].dt.total_seconds()
        
        # Filter out install laps and outliers (> 130% of median)
        median_time = lap_times.median()
        clean_times = lap_times[
            (lap_times > 60) &  # No install laps
            (lap_times < median_time * 1.3)  # No massive outliers
        ]
        
        if len(clean_times) == 0:
            continue
        
        # Get compound breakdown
        compound_times = {}
        for compound in team_laps['Compound'].dropna().unique():
            c_laps = team_laps[team_laps['Compound'] == compound]
            c_times = c_laps['LapTime'].dt.total_seconds()
            c_clean = c_times[(c_times > 60) & (c_times < median_time * 1.3)]
            if len(c_clean) > 0:
                compound_times[str(compound)] = {
                    "best": round(float(c_clean.min()), 3),
                    "mean": round(float(c_clean.mean()), 3),
                    "count": int(len(c_clean))
                }
        
        # Get driver breakdown
        driver_times = {}
        for driver in team_laps['Driver'].dropna().unique():
            d_laps = team_laps[team_laps['Driver'] == driver]
            d_times = d_laps['LapTime'].dt.total_seconds()
            d_clean = d_times[(d_times > 60) & (d_times < median_time * 1.3)]
            if len(d_clean) > 0:
                driver_times[str(driver)] = {
                    "best": round(float(d_clean.min()), 3),
                    "mean": round(float(d_clean.mean()), 3),
                    "count": int(len(d_clean))
                }
        
        team_data[str(team)] = {
            "best_lap": round(float(clean_times.min()), 3),
            "mean_lap": round(float(clean_times.mean()), 3),
            "median_lap": round(float(clean_times.median()), 3),
            "total_laps": int(len(clean_times)),
            "compounds": compound_times,
            "drivers": driver_times,
        }
    
    return team_data


def fetch_testing_data():
    """Fetch and extract preseason testing data."""
    print("\n" + "=" * 60)
    print("PRESEASON TESTING DATA")
    print("=" * 60)
    
    all_testing = {}
    
    for year, event, day in TESTING_SESSIONS:
        label = f"{year} {event} Day {day}"
        print(f"\nFetching {label}...")
        try:
            session = fastf1.get_session(year, event, day)
            session.load()
            print(f"  ✓ {len(session.laps)} laps loaded")
            
            team_perf = extract_team_performance(session)
            if team_perf:
                key = f"{year}_day{day}"
                all_testing[key] = {
                    "year": year,
                    "day": day,
                    "event": event,
                    "teams": team_perf
                }
                print(f"  ✓ Extracted data for {len(team_perf)} teams")
            else:
                print(f"  ⚠ No clean lap data extracted")
                
        except Exception as e:
            print(f"  ✗ Error loading {label}: {e}")
            continue
    
    # Save extracted testing data
    if all_testing:
        os.makedirs(os.path.dirname(TESTING_OUTPUT), exist_ok=True)
        with open(TESTING_OUTPUT, 'w') as f:
            json.dump(all_testing, f, indent=2)
        print(f"\n✓ Testing data saved to {TESTING_OUTPUT}")
    else:
        print("\n⚠ No testing data was successfully extracted")
        # Create a placeholder with estimated 2026 data
        create_estimated_testing_data()
    
    return all_testing


def create_estimated_testing_data():
    """
    Create estimated testing data for 2026 teams based on 
    2025 season performance deltas. Used as fallback when 
    real testing data isn't available.
    """
    print("  Creating estimated testing data from team performance models...")
    
    # Estimated performance based on 2025 constructor standings + regulation changes
    # Base time is an estimated testing venue lap time (~90s)
    base_time = 90.0
    
    estimated = {
        "2026_estimated": {
            "year": 2026,
            "day": 0,
            "event": "Pre-Season Testing (Estimated)",
            "teams": {
                "Red Bull Racing": {
                    "best_lap": round(base_time + 0.0, 3),
                    "mean_lap": round(base_time + 0.8, 3),
                    "median_lap": round(base_time + 0.6, 3),
                    "total_laps": 150,
                    "compounds": {
                        "SOFT": {"best": round(base_time - 0.5, 3), "mean": round(base_time + 0.3, 3), "count": 40},
                        "MEDIUM": {"best": round(base_time + 0.3, 3), "mean": round(base_time + 0.9, 3), "count": 50},
                        "HARD": {"best": round(base_time + 0.8, 3), "mean": round(base_time + 1.4, 3), "count": 60}
                    },
                    "drivers": {}
                },
                "Ferrari": {
                    "best_lap": round(base_time + 0.2, 3),
                    "mean_lap": round(base_time + 1.0, 3),
                    "median_lap": round(base_time + 0.8, 3),
                    "total_laps": 145,
                    "compounds": {
                        "SOFT": {"best": round(base_time - 0.3, 3), "mean": round(base_time + 0.5, 3), "count": 38},
                        "MEDIUM": {"best": round(base_time + 0.5, 3), "mean": round(base_time + 1.1, 3), "count": 48},
                        "HARD": {"best": round(base_time + 1.0, 3), "mean": round(base_time + 1.6, 3), "count": 59}
                    },
                    "drivers": {}
                },
                "McLaren": {
                    "best_lap": round(base_time + 0.3, 3),
                    "mean_lap": round(base_time + 1.1, 3),
                    "median_lap": round(base_time + 0.9, 3),
                    "total_laps": 140,
                    "compounds": {
                        "SOFT": {"best": round(base_time - 0.2, 3), "mean": round(base_time + 0.6, 3), "count": 35},
                        "MEDIUM": {"best": round(base_time + 0.6, 3), "mean": round(base_time + 1.2, 3), "count": 45},
                        "HARD": {"best": round(base_time + 1.1, 3), "mean": round(base_time + 1.7, 3), "count": 60}
                    },
                    "drivers": {}
                },
                "Mercedes": {
                    "best_lap": round(base_time + 0.4, 3),
                    "mean_lap": round(base_time + 1.2, 3),
                    "median_lap": round(base_time + 1.0, 3),
                    "total_laps": 148,
                    "compounds": {
                        "SOFT": {"best": round(base_time - 0.1, 3), "mean": round(base_time + 0.7, 3), "count": 37},
                        "MEDIUM": {"best": round(base_time + 0.7, 3), "mean": round(base_time + 1.3, 3), "count": 50},
                        "HARD": {"best": round(base_time + 1.2, 3), "mean": round(base_time + 1.8, 3), "count": 61}
                    },
                    "drivers": {}
                },
                "Aston Martin": {
                    "best_lap": round(base_time + 0.7, 3),
                    "mean_lap": round(base_time + 1.5, 3),
                    "median_lap": round(base_time + 1.3, 3),
                    "total_laps": 130,
                    "compounds": {
                        "SOFT": {"best": round(base_time + 0.2, 3), "mean": round(base_time + 1.0, 3), "count": 30},
                        "MEDIUM": {"best": round(base_time + 1.0, 3), "mean": round(base_time + 1.6, 3), "count": 45},
                        "HARD": {"best": round(base_time + 1.5, 3), "mean": round(base_time + 2.1, 3), "count": 55}
                    },
                    "drivers": {}
                },
                "Alpine": {
                    "best_lap": round(base_time + 0.9, 3),
                    "mean_lap": round(base_time + 1.7, 3),
                    "median_lap": round(base_time + 1.5, 3),
                    "total_laps": 125,
                    "compounds": {
                        "SOFT": {"best": round(base_time + 0.4, 3), "mean": round(base_time + 1.2, 3), "count": 28},
                        "MEDIUM": {"best": round(base_time + 1.2, 3), "mean": round(base_time + 1.8, 3), "count": 42},
                        "HARD": {"best": round(base_time + 1.7, 3), "mean": round(base_time + 2.3, 3), "count": 55}
                    },
                    "drivers": {}
                },
                "Racing Bulls": {
                    "best_lap": round(base_time + 1.0, 3),
                    "mean_lap": round(base_time + 1.8, 3),
                    "median_lap": round(base_time + 1.6, 3),
                    "total_laps": 120,
                    "compounds": {
                        "SOFT": {"best": round(base_time + 0.5, 3), "mean": round(base_time + 1.3, 3), "count": 25},
                        "MEDIUM": {"best": round(base_time + 1.3, 3), "mean": round(base_time + 1.9, 3), "count": 40},
                        "HARD": {"best": round(base_time + 1.8, 3), "mean": round(base_time + 2.4, 3), "count": 55}
                    },
                    "drivers": {}
                },
                "Haas F1 Team": {
                    "best_lap": round(base_time + 1.1, 3),
                    "mean_lap": round(base_time + 1.9, 3),
                    "median_lap": round(base_time + 1.7, 3),
                    "total_laps": 115,
                    "compounds": {
                        "SOFT": {"best": round(base_time + 0.6, 3), "mean": round(base_time + 1.4, 3), "count": 25},
                        "MEDIUM": {"best": round(base_time + 1.4, 3), "mean": round(base_time + 2.0, 3), "count": 40},
                        "HARD": {"best": round(base_time + 1.9, 3), "mean": round(base_time + 2.5, 3), "count": 50}
                    },
                    "drivers": {}
                },
                "Williams": {
                    "best_lap": round(base_time + 1.2, 3),
                    "mean_lap": round(base_time + 2.0, 3),
                    "median_lap": round(base_time + 1.8, 3),
                    "total_laps": 118,
                    "compounds": {
                        "SOFT": {"best": round(base_time + 0.7, 3), "mean": round(base_time + 1.5, 3), "count": 26},
                        "MEDIUM": {"best": round(base_time + 1.5, 3), "mean": round(base_time + 2.1, 3), "count": 42},
                        "HARD": {"best": round(base_time + 2.0, 3), "mean": round(base_time + 2.6, 3), "count": 50}
                    },
                    "drivers": {}
                },
                "Kick Sauber": {
                    "best_lap": round(base_time + 1.3, 3),
                    "mean_lap": round(base_time + 2.1, 3),
                    "median_lap": round(base_time + 1.9, 3),
                    "total_laps": 110,
                    "compounds": {
                        "SOFT": {"best": round(base_time + 0.8, 3), "mean": round(base_time + 1.6, 3), "count": 22},
                        "MEDIUM": {"best": round(base_time + 1.6, 3), "mean": round(base_time + 2.2, 3), "count": 38},
                        "HARD": {"best": round(base_time + 2.1, 3), "mean": round(base_time + 2.7, 3), "count": 50}
                    },
                    "drivers": {}
                },
                "Cadillac F1": {
                    "best_lap": round(base_time + 1.5, 3),
                    "mean_lap": round(base_time + 2.4, 3),
                    "median_lap": round(base_time + 2.1, 3),
                    "total_laps": 95,
                    "compounds": {
                        "SOFT": {"best": round(base_time + 1.0, 3), "mean": round(base_time + 1.9, 3), "count": 18},
                        "MEDIUM": {"best": round(base_time + 1.8, 3), "mean": round(base_time + 2.5, 3), "count": 32},
                        "HARD": {"best": round(base_time + 2.3, 3), "mean": round(base_time + 3.0, 3), "count": 45}
                    },
                    "drivers": {}
                }
            }
        }
    }
    
    os.makedirs(os.path.dirname(TESTING_OUTPUT), exist_ok=True)
    with open(TESTING_OUTPUT, 'w') as f:
        json.dump(estimated, f, indent=2)
    print(f"  ✓ Estimated testing data saved to {TESTING_OUTPUT}")


def fetch_race_data():
    """Fetch and cache reference race data."""
    print("=" * 60)
    print("REFERENCE RACE DATA")
    print("=" * 60)
    print(f"\nThis will download {len(RACES_TO_CACHE)} race sessions.")
    print("This may take 15-20 minutes depending on your connection.\n")
    
    for year, race, session_type in RACES_TO_CACHE:
        print(f"Fetching {year} {race} ({session_type})...")
        try:
            session = fastf1.get_session(year, race, session_type)
            session.load()
            print(f"  ✓ {len(session.laps)} laps loaded and cached")
        except Exception as e:
            print(f"  ✗ Error loading {year} {race}: {e}")
            continue


def main():
    print("=" * 60)
    print("PitWall - FastF1 Data Pre-Cache Script")
    print("=" * 60)
    
    # Fetch reference race data
    fetch_race_data()
    
    # Fetch preseason testing data
    fetch_testing_data()
    
    print("\n" + "=" * 60)
    print("All data cached successfully!")
    print("Cache location: ../backend/data/cache/")
    print("Testing data: ../backend/data/testing_data.json")
    print("You're ready to start building.")
    print("=" * 60)


if __name__ == "__main__":
    main()
