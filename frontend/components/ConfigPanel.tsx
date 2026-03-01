'use client';

import { useState, useEffect } from 'react';
import { getTracks, getTeams, getMonthName, type RaceConfig, type TeamInfo, type TrackInfo, type DriverInfo } from '@/lib/api';

interface ConfigPanelProps {
  onOptimize: (config: RaceConfig) => void;
  isLoading: boolean;
}

// Helper to describe a trait value with 4-tier scale matching real driver data
function traitLabel(
  value: number,
  eliteLabel: string,
  goodLabel: string,
  avgLabel: string,
  poorLabel: string
): { label: string; color: string } {
  if (value <= 0.86) return { label: eliteLabel, color: 'text-emerald-400' };
  if (value <= 0.92) return { label: goodLabel, color: 'text-green-400' };
  if (value <= 0.97) return { label: avgLabel, color: 'text-yellow-400' };
  return { label: poorLabel, color: 'text-red-400' };
}

export default function ConfigPanel({ onOptimize, isLoading }: ConfigPanelProps) {
  const [tracks, setTracks] = useState<TrackInfo[]>([]);
  const [teams, setTeams] = useState<TeamInfo[]>([]);
  const [config, setConfig] = useState<RaceConfig>({
    track: 'australia',
    total_laps: 58,
    starting_compound: 'SOFT',
    fuel_load_kg: 70,       // 2026 regs: ~70kg fuel limit
    rain_probability: 0.15, // Will be auto-set from track data
    safety_car_probability: 0.2,
    team: null,
    driver: null,
  });

  useEffect(() => {
    getTracks().then((trackList) => {
      setTracks(trackList);
      // Auto-set rain, safety car, and recommended starting compound for initial track
      const initial = trackList.find(t => t.id === 'australia');
      if (initial) {
        setConfig(prev => ({
          ...prev,
          rain_probability: initial.historical_rain_pct,
          safety_car_probability: initial.historical_safety_car_pct ?? 0.2,
          starting_compound: (initial.recommended_start_compound ?? 'MEDIUM') as RaceConfig['starting_compound'],
        }));
      }
    }).catch(console.error);
    getTeams().then(setTeams).catch(console.error);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onOptimize(config);
  };

  const selectedTeam = teams.find(t => t.id === config.team);
  const selectedTrack = tracks.find(t => t.id === config.track);

  // Get drivers for the selected team
  const teamDrivers: [string, DriverInfo][] = selectedTeam
    ? Object.entries(selectedTeam.drivers)
    : [];

  // Get selected driver info
  const selectedDriver: DriverInfo | undefined = selectedTeam && config.driver
    ? selectedTeam.drivers[config.driver]
    : undefined;

  // Format rain intensity label
  const rainIntensityLabel = selectedTrack?.rain_intensity
    ? selectedTrack.rain_intensity.charAt(0).toUpperCase() + selectedTrack.rain_intensity.slice(1)
    : '';

  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg">
      <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">Race Configuration</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Team Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Team
          </label>
          <select
            value={config.team || ''}
            onChange={(e) => {
              const team = e.target.value || null;
              setConfig({ ...config, team, driver: null }); // Reset driver on team change
            }}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="">Generic Car (No Team)</option>
            {teams.map((team) => (
              <option key={team.id} value={team.id}>
                {team.name} ({team.short}) — +{team.base_delta.toFixed(1)}s
              </option>
            ))}
          </select>
          {/* Team badge */}
          {selectedTeam && (
            <div className="mt-2 flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: selectedTeam.color }}
              />
              <span className="text-xs text-gray-500 dark:text-gray-400">
                Pit crew: +{selectedTeam.pit_crew_delta.toFixed(1)}s | Tire wear: {((selectedTeam.tire_wear_factor - 1) * 100).toFixed(0)}% extra
              </span>
            </div>
          )}
        </div>

        {/* Driver Selection - only shown when team is selected */}
        {selectedTeam && teamDrivers.length > 0 && (
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Driver
            </label>
            <select
              value={config.driver || ''}
              onChange={(e) => {
                const driver = e.target.value || null;
                setConfig({ ...config, driver });
              }}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value="">Team Average (Both Drivers)</option>
              {teamDrivers.map(([driverId, driver]) => (
                <option key={driverId} value={driverId}>
                  #{driver.number} {driver.name}
                </option>
              ))}
            </select>

            {/* Driver traits card */}
            {selectedDriver && (
              <div className="mt-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600">
                <div className="flex items-center gap-2 mb-2">
                  <div
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: selectedTeam.color }}
                  />
                  <span className="text-sm font-bold text-gray-900 dark:text-white">
                    #{selectedDriver.number} {selectedDriver.name}
                  </span>
                </div>
                
                <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
                  {/* Pace Delta */}
                  <div className="flex justify-between">
                    <span className="text-gray-500 dark:text-gray-400">Pace vs Teammate</span>
                    <span className={`font-mono font-bold ${selectedDriver.pace_delta === 0 ? 'text-green-400' : selectedDriver.pace_delta <= 0.15 ? 'text-yellow-400' : 'text-red-400'}`}>
                      {selectedDriver.pace_delta === 0 ? 'Lead' : `+${selectedDriver.pace_delta.toFixed(2)}s`}
                    </span>
                  </div>

                  {/* Tire Management */}
                  <div className="flex justify-between">
                    <span className="text-gray-500 dark:text-gray-400">Tire Management</span>
                    <span className={`font-bold ${traitLabel(selectedDriver.tire_management, 'Legendary', 'Excellent', 'Good', 'Aggressive').color}`}>
                      {traitLabel(selectedDriver.tire_management, 'Legendary', 'Excellent', 'Good', 'Aggressive').label}
                    </span>
                  </div>

                  {/* Wet Skill */}
                  <div className="flex justify-between">
                    <span className="text-gray-500 dark:text-gray-400">Wet Weather</span>
                    <span className={`font-bold ${traitLabel(selectedDriver.wet_skill, 'Rain Master', 'Exceptional', 'Strong', 'Average').color}`}>
                      {traitLabel(selectedDriver.wet_skill, 'Rain Master', 'Exceptional', 'Strong', 'Average').label}
                    </span>
                  </div>

                  {/* Consistency */}
                  <div className="flex justify-between">
                    <span className="text-gray-500 dark:text-gray-400">Consistency</span>
                    <span className={`font-bold ${traitLabel(selectedDriver.consistency, 'Metronomic', 'Very High', 'Consistent', 'Variable').color}`}>
                      {traitLabel(selectedDriver.consistency, 'Metronomic', 'Very High', 'Consistent', 'Variable').label}
                    </span>
                  </div>

                  {/* Overtaking */}
                  <div className="col-span-2 flex justify-between">
                    <span className="text-gray-500 dark:text-gray-400">Overtaking</span>
                    <span className={`font-bold ${selectedDriver.overtaking_delta <= -0.10 ? 'text-green-400' : selectedDriver.overtaking_delta <= -0.03 ? 'text-yellow-400' : 'text-red-400'}`}>
                      {selectedDriver.overtaking_delta <= -0.10 ? 'Elite Overtaker' : selectedDriver.overtaking_delta <= -0.03 ? 'Strong' : selectedDriver.overtaking_delta <= 0 ? 'Average' : 'Defensive'}
                    </span>
                  </div>
                </div>

                {/* Visual trait bars */}
                <div className="mt-2 space-y-1">
                  {[
                    { label: 'Tire Mgmt', value: 1 - (selectedDriver.tire_management - 0.8) / 0.4, color: 'bg-emerald-500' },
                    { label: 'Wet Skill', value: 1 - (selectedDriver.wet_skill - 0.7) / 0.4, color: 'bg-blue-500' },
                    { label: 'Consistency', value: 1 - (selectedDriver.consistency - 0.8) / 0.4, color: 'bg-purple-500' },
                    { label: 'Overtaking', value: Math.min(1, (Math.abs(selectedDriver.overtaking_delta) + 0.05) / 0.2), color: 'bg-orange-500' },
                  ].map((trait) => (
                    <div key={trait.label} className="flex items-center gap-2">
                      <span className="text-[10px] text-gray-400 w-16 text-right">{trait.label}</span>
                      <div className="flex-1 bg-gray-200 dark:bg-gray-600 rounded-full h-1.5">
                        <div
                          className={`h-full rounded-full ${trait.color}`}
                          style={{ width: `${Math.max(5, Math.min(100, trait.value * 100))}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Track Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Track
          </label>
          <select
            value={config.track}
            onChange={(e) => {
              const trackId = e.target.value;
              const trackInfo = tracks.find(t => t.id === trackId);
              const recommended = trackInfo?.recommended_start_compound ?? 'SOFT';
              setConfig({ 
                ...config, 
                track: trackId,
                total_laps: trackInfo?.laps || 57,
                rain_probability: trackInfo?.historical_rain_pct ?? 0.15,
                safety_car_probability: trackInfo?.historical_safety_car_pct ?? 0.2,
                starting_compound: recommended as RaceConfig['starting_compound'],
              });
            }}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            {tracks.map((track) => (
              <option key={track.id} value={track.id}>
                {track.name} ({track.laps} laps) — {getMonthName(track.race_month)}
              </option>
            ))}
          </select>
          {selectedTrack && (
            <div className="mt-1 space-y-0.5">
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {selectedTrack.circuit}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Race month: {getMonthName(selectedTrack.race_month)} | Historical rain: {(selectedTrack.historical_rain_pct * 100).toFixed(0)}% ({rainIntensityLabel})
              </p>
            </div>
          )}
        </div>

        {/* Starting Compound */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Starting Compound
            {selectedTrack?.recommended_start_compound && (
              <span className="ml-2 text-xs font-normal text-emerald-600 dark:text-emerald-400">
                (Recommended for {selectedTrack.name}: {selectedTrack.recommended_start_compound})
              </span>
            )}
          </label>
          {/* Dry compounds */}
          <div className="flex gap-2 mb-2">
            {(['SOFT', 'MEDIUM', 'HARD'] as const).map((compound) => (
              <button
                key={compound}
                type="button"
                onClick={() => setConfig({ ...config, starting_compound: compound })}
                className={`flex-1 py-2 px-3 rounded-md font-medium text-sm transition ${
                  config.starting_compound === compound
                    ? compound === 'SOFT'
                      ? 'bg-red-500 text-white ring-2 ring-red-300'
                      : compound === 'MEDIUM'
                      ? 'bg-yellow-500 text-white ring-2 ring-yellow-300'
                      : 'bg-gray-500 text-white ring-2 ring-gray-300'
                    : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
                }`}
              >
                {compound}
              </button>
            ))}
          </div>
          {/* Wet compounds */}
          <div className="flex gap-2">
            {(['INTERMEDIATE', 'WET'] as const).map((compound) => (
              <button
                key={compound}
                type="button"
                onClick={() => setConfig({ ...config, starting_compound: compound })}
                className={`flex-1 py-2 px-3 rounded-md font-medium text-sm transition ${
                  config.starting_compound === compound
                    ? compound === 'INTERMEDIATE'
                      ? 'bg-green-500 text-white ring-2 ring-green-300'
                      : 'bg-blue-500 text-white ring-2 ring-blue-300'
                    : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
                }`}
              >
                {compound}
              </button>
            ))}
          </div>
        </div>

        {/* Rain Probability */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Rain Probability: {(config.rain_probability * 100).toFixed(0)}%
            {selectedTrack && (
              <span className="text-xs text-gray-400 ml-2">
                (historical: {(selectedTrack.historical_rain_pct * 100).toFixed(0)}%)
              </span>
            )}
          </label>
          <input
            type="range"
            min="0"
            max="100"
            value={config.rain_probability * 100}
            onChange={(e) =>
              setConfig({ ...config, rain_probability: Number(e.target.value) / 100 })
            }
            className="w-full"
          />
          {config.rain_probability > 0 && (
            <p className="text-xs text-blue-500 dark:text-blue-400 mt-1">
              {Math.round(500 * config.rain_probability)} of 500 Monte Carlo sims will have rain
            </p>
          )}
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={isLoading}
          className="w-full bg-red-600 hover:bg-red-700 disabled:bg-gray-400 text-white font-bold py-3 px-4 rounded-md transition"
        >
          {isLoading ? 'Optimizing...' : 'Optimize Strategy'}
        </button>
      </form>
    </div>
  );
}
