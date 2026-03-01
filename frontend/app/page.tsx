'use client';

import { useState } from 'react';
import ConfigPanel from '@/components/ConfigPanel';
import AIBrief from '@/components/AIBrief';
import EmergencyStrategies from '@/components/EmergencyStrategies';
import StrategyChart from '@/components/StrategyChart';
import ComparisonTable from '@/components/ComparisonTable';
import RobustnessChart from '@/components/RobustnessChart';
import { optimize, type RaceConfig, type OptimizeResponse } from '@/lib/api';

export default function Home() {
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<OptimizeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleOptimize = async (config: RaceConfig) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await optimize(config);
      setResult(response);
    } catch (err: any) {
      setError(err.message || 'Optimization failed');
      console.error('Optimization error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-4 md:p-8">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <h1 className="text-5xl font-bold text-white mb-2">
          PitWall
        </h1>
        <p className="text-gray-400 text-lg">
          Formula 1 Race Strategy Optimizer — Powered by AI & Monte Carlo Simulation
        </p>
      </div>

      {/* Error Message */}
      {error && (
        <div className="max-w-7xl mx-auto mb-6">
          <div className="bg-red-900/50 border border-red-500 text-red-200 p-4 rounded-lg">
            <strong>Error:</strong> {error}
          </div>
        </div>
      )}

      {/* Main Layout */}
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Top Row: Config Panel + AI Brief */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ConfigPanel onOptimize={handleOptimize} isLoading={isLoading} />
          <div className="space-y-4">
            <AIBrief brief={result?.ai_brief || ''} />
            {/* Team Info Badge */}
            {result?.team_info && (
              <div 
                className="p-4 rounded-lg border-2"
                style={{ borderColor: result.team_info.color, backgroundColor: `${result.team_info.color}15` }}
              >
                <div className="flex items-center gap-3 mb-2">
                  <div
                    className="w-4 h-4 rounded-full"
                    style={{ backgroundColor: result.team_info.color }}
                  />
                  <h3 className="text-lg font-bold text-white">
                    {result.team_info.name}
                  </h3>
                  <span className="text-xs font-mono text-gray-400 bg-gray-800 px-2 py-1 rounded">
                    {result.team_info.short}
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="text-gray-400 block text-xs">Pace Delta</span>
                    <span className="text-white font-mono">+{result.team_info.base_delta.toFixed(1)}s</span>
                  </div>
                  <div>
                    <span className="text-gray-400 block text-xs">Pit Crew</span>
                    <span className="text-white font-mono">+{result.team_info.pit_crew_delta.toFixed(1)}s</span>
                  </div>
                  <div>
                    <span className="text-gray-400 block text-xs">Tire Wear</span>
                    <span className="text-white font-mono">{result.team_info.tire_wear_factor.toFixed(2)}x</span>
                  </div>
                </div>
                <div className="mt-2 text-xs text-gray-400">
                  Drivers: {Object.values(result.team_info.drivers).map(d => d.name).join(' • ')}
                </div>
              </div>
            )}
            {/* Driver Info Badge */}
            {result?.driver_info && (
              <div className="p-4 rounded-lg border border-gray-600 bg-gray-700/30">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-mono text-gray-400 bg-gray-800 px-2 py-0.5 rounded">
                    #{result.driver_info.number}
                  </span>
                  <h3 className="text-md font-bold text-white">
                    {result.driver_info.name}
                  </h3>
                  <span className="text-[10px] text-gray-500 ml-auto">Strategy optimized for this driver</span>
                </div>
                <div className="grid grid-cols-5 gap-2 text-xs">
                  <div className="text-center">
                    <span className="text-gray-400 block">Pace</span>
                    <span className="text-white font-mono">{result.driver_info.pace_delta === 0 ? 'Lead' : `+${result.driver_info.pace_delta.toFixed(2)}s`}</span>
                  </div>
                  <div className="text-center">
                    <span className="text-gray-400 block">Tires</span>
                    <span className="text-white font-mono">{result.driver_info.tire_management.toFixed(2)}x</span>
                  </div>
                  <div className="text-center">
                    <span className="text-gray-400 block">Wet</span>
                    <span className="text-white font-mono">{result.driver_info.wet_skill.toFixed(2)}x</span>
                  </div>
                  <div className="text-center">
                    <span className="text-gray-400 block">Consistency</span>
                    <span className="text-white font-mono">{result.driver_info.consistency.toFixed(2)}x</span>
                  </div>
                  <div className="text-center">
                    <span className="text-gray-400 block">Overtake</span>
                    <span className="text-white font-mono">{result.driver_info.overtaking_delta.toFixed(2)}s</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="bg-white dark:bg-gray-800 p-8 rounded-lg shadow-lg text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-300 border-t-red-600 mb-4"></div>
            <p className="text-gray-600 dark:text-gray-400">
              Running optimization... This may take 20-30 seconds.
            </p>
          </div>
        )}

        {/* Results */}
        {result && !isLoading && (
          <>
            {/* Strategy Chart */}
            <StrategyChart 
              strategies={result.strategies} 
              totalLaps={result.config.total_laps}
            />

            {/* Comparison Table */}
            <ComparisonTable strategies={result.strategies} />

            {/* Emergency / contingency pit strategies */}
            <EmergencyStrategies advice={result?.emergency_advice} />

            {/* Robustness Chart */}
            <RobustnessChart strategies={result.strategies} />
          </>
        )}

        {/* Welcome Message */}
        {!result && !isLoading && (
          <div className="bg-white dark:bg-gray-800 p-12 rounded-lg shadow-lg text-center">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
              Welcome to PitWall
            </h2>
            <p className="text-gray-600 dark:text-gray-400 max-w-2xl mx-auto mb-6">
              Configure your race parameters above and click <strong>Optimize Strategy</strong> to generate
              the optimal pit stop strategy. Our engine simulates thousands of scenarios using Monte Carlo
              analysis and provides AI-powered race engineer insights.
            </p>
            <div className="bg-gray-100 dark:bg-gray-700/50 p-4 rounded-lg inline-block text-left">
              <h3 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-2">2026 Grid — 11 Teams</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Select a team from the dropdown to optimize strategy for a specific car's performance profile,
                including pace delta, pit crew speed, and tire wear characteristics.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="max-w-7xl mx-auto mt-12 pt-8 border-t border-gray-700 text-center text-gray-500 text-sm">
        <p>
          PitWall — Built with FastAPI, FastF1, Claude AI, and Next.js
        </p>
      </footer>
    </main>
  );
}
