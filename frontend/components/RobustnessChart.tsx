'use client';

import type { Strategy } from '@/lib/api';

interface RobustnessChartProps {
  strategies: Strategy[];
}

export default function RobustnessChart({ strategies }: RobustnessChartProps) {
  const optimal = strategies.find(s => s.tag === 'OPTIMAL') ?? null;
  const variable = strategies.find(s => s.tag === 'VARIABLE') ?? null;

  if (!optimal) {
    return (
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg">
        <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">Robustness Analysis</h2>
        <p className="text-gray-600 dark:text-gray-400">Run optimization to see robustness metrics...</p>
      </div>
    );
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(1);
    return `${mins}:${secs.padStart(4, '0')}`;
  };

  const renderColumn = (
    strategy: Strategy,
    label: string,
    accentColor: string,
    borderColor: string,
    bgClass: string,
  ) => (
    <div className={`rounded-lg border-2 p-4 ${bgClass}`} style={{ borderColor }}>
      <h3 className="text-sm font-bold uppercase tracking-wider mb-3" style={{ color: accentColor }}>
        {label}
      </h3>

      {/* Robustness Bar */}
      <div className="mb-4">
        <div className="text-3xl font-bold text-gray-900 dark:text-white mb-1">
          {strategy.robustness_score.toFixed(1)}
          <span className="text-base text-gray-500 dark:text-gray-400">/100</span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-3 overflow-hidden">
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${strategy.robustness_score}%`,
              background: `linear-gradient(to right, #ef4444, #f59e0b, #10b981)`,
            }}
          />
        </div>
      </div>

      {/* Pit Plan */}
      <div className="mb-3">
        <span className="text-xs text-gray-500 dark:text-gray-400 block mb-1">Pit Plan</span>
        <div className="flex flex-wrap gap-1">
          {strategy.stops.map((stop, i) => {
            const colors: Record<string, string> = {
              SOFT: 'bg-red-500', MEDIUM: 'bg-yellow-500', HARD: 'bg-gray-400',
              INTERMEDIATE: 'bg-green-500', WET: 'bg-blue-500',
            };
            return (
              <span key={i} className={`${colors[stop.compound] || 'bg-purple-500'} text-white px-2 py-0.5 rounded text-xs font-medium`}>
                L{stop.lap} → {stop.compound}
              </span>
            );
          })}
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-3 gap-2">
        <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded border border-blue-200 dark:border-blue-800">
          <div className="text-[10px] text-blue-600 dark:text-blue-400 mb-0.5">Mean</div>
          <div className="text-sm font-mono font-bold text-gray-900 dark:text-white">
            {formatTime(strategy.total_race_time_seconds)}
          </div>
        </div>
        <div className="p-2 bg-green-50 dark:bg-green-900/20 rounded border border-green-200 dark:border-green-800">
          <div className="text-[10px] text-green-600 dark:text-green-400 mb-0.5">P50</div>
          <div className="text-sm font-mono font-bold text-gray-900 dark:text-white">
            {formatTime(strategy.p50_time)}
          </div>
        </div>
        <div className="p-2 bg-orange-50 dark:bg-orange-900/20 rounded border border-orange-200 dark:border-orange-800">
          <div className="text-[10px] text-orange-600 dark:text-orange-400 mb-0.5">P90</div>
          <div className="text-sm font-mono font-bold text-gray-900 dark:text-white">
            {formatTime(strategy.p90_time)}
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg">
      <h2 className="text-2xl font-bold mb-2 text-gray-900 dark:text-white">Robustness Analysis</h2>
      <div className="text-sm text-gray-600 dark:text-gray-400 mb-4">
        Monte Carlo simulation results (500 runs) — comparing best optimal vs best variable strategy
      </div>

      <div className={`grid gap-4 ${variable ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1 max-w-md'}`}>
        {renderColumn(
          optimal,
          'Best Optimal (fastest P50)',
          '#10b981',
          '#10b981',
          'bg-green-50/50 dark:bg-green-900/10',
        )}
        {variable && renderColumn(
          variable,
          'Best Variable (highest robustness)',
          '#f59e0b',
          '#f59e0b',
          'bg-amber-50/50 dark:bg-amber-900/10',
        )}
      </div>

      {/* Interpretation */}
      <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg text-sm">
        <p className="text-gray-700 dark:text-gray-300">
          <strong>OPTIMAL</strong> is the fastest strategy under ideal conditions (best P50 time).
          {' '}<strong>VARIABLE</strong> is the most consistent under uncertainty (highest robustness score, best P90).
          {' '}In dry conditions prefer OPTIMAL; when rain/safety cars are likely, VARIABLE may be the safer pick.
        </p>
      </div>
    </div>
  );
}
