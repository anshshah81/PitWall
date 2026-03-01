/**
 * API Client for PitWall Backend
 * Handles all communication with FastAPI server
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface PitStop {
  lap: number;
  compound: 'SOFT' | 'MEDIUM' | 'HARD' | 'INTERMEDIATE' | 'WET';
}

export interface Strategy {
  stops: PitStop[];
  total_race_time_seconds: number;
  robustness_score: number;
  p50_time: number;
  p90_time: number;
  tag?: 'OPTIMAL' | 'VARIABLE' | null;
}

export interface RaceConfig {
  track: string;
  total_laps: number;
  starting_compound: 'SOFT' | 'MEDIUM' | 'HARD' | 'INTERMEDIATE' | 'WET';
  fuel_load_kg: number;
  rain_probability: number;
  safety_car_probability: number;
  team?: string | null;
  driver?: string | null;
}

export interface DriverInfo {
  id: string;
  name: string;
  number: number;
  pace_delta: number;
  tire_management: number;
  wet_skill: number;
  consistency: number;
  overtaking_delta: number;
}

export interface TeamInfo {
  id: string;
  name: string;
  short: string;
  color: string;
  base_delta: number;
  pit_crew_delta: number;
  tire_wear_factor: number;
  drivers: Record<string, DriverInfo>;
}

export interface OptimizeResponse {
  strategies: Strategy[];
  ai_brief: string;
  config: RaceConfig;
  team_info?: TeamInfo | null;
  driver_info?: DriverInfo | null;
}

export interface TestingCompoundData {
  best: number;
  mean: number;
  count: number;
}

export interface TestingDriverData {
  best: number;
  mean: number;
  count: number;
}

export interface TestingTeamData {
  best_lap: number;
  mean_lap: number;
  median_lap: number;
  total_laps: number;
  compounds: Record<string, TestingCompoundData>;
  drivers: Record<string, TestingDriverData>;
}

export interface TestingSession {
  year: number;
  day: number;
  event: string;
  teams: Record<string, TestingTeamData>;
}

export interface TrackInfo {
  id: string;
  name: string;
  circuit: string;
  laps: number;
  pit_loss: number;
  base_lap_time: number;
  race_month: number;
  historical_rain_pct: number;
  rain_intensity: 'light' | 'moderate' | 'heavy';
}

const MONTH_NAMES = [
  '', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
];

export function getMonthName(month: number): string {
  return MONTH_NAMES[month] || '';
}

export async function getTracks(): Promise<TrackInfo[]> {
  const res = await fetch(`${BASE_URL}/tracks`);
  if (!res.ok) {
    throw new Error('Failed to fetch tracks');
  }
  const data = await res.json();
  return data.tracks;
}

export async function getTeams(): Promise<TeamInfo[]> {
  const res = await fetch(`${BASE_URL}/teams`);
  if (!res.ok) {
    throw new Error('Failed to fetch teams');
  }
  const data = await res.json();
  return data.teams;
}

export async function getTeam(teamId: string): Promise<TeamInfo> {
  const res = await fetch(`${BASE_URL}/teams/${teamId}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch team ${teamId}`);
  }
  return res.json();
}

export async function getTestingData(): Promise<Record<string, TestingSession>> {
  const res = await fetch(`${BASE_URL}/testing`);
  if (!res.ok) {
    throw new Error('Failed to fetch testing data');
  }
  const data = await res.json();
  return data.testing_sessions;
}

export async function getTeamTestingData(teamId: string): Promise<{
  team_id: string;
  team_name: string;
  testing_data: Record<string, TestingTeamData>;
}> {
  const res = await fetch(`${BASE_URL}/testing/${teamId}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch testing data for ${teamId}`);
  }
  return res.json();
}

export async function optimize(config: RaceConfig): Promise<OptimizeResponse> {
  const res = await fetch(`${BASE_URL}/optimize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Optimization failed');
  }
  
  return res.json();
}

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE_URL}/health`);
    return res.ok;
  } catch {
    return false;
  }
}
