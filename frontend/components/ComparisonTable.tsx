'use client';

import type { Strategy } from '@/lib/api';

interface ComparisonTableProps {
  strategies: Strategy[];
}

export default function ComparisonTable({ strategies }: ComparisonTableProps) {
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(1);
    return `${mins}:${secs.padStart(4, '0')}`;
  };

  const getCompoundColor = (compound: string) => {
    switch (compound) {
      case 'SOFT': return 'bg-red-500';
      case 'MEDIUM': return 'bg-yellow-500';
      case 'HARD': return 'bg-gray-400';
      case 'INTERMEDIATE': return 'bg-green-500';
      case 'WET': return 'bg-blue-500';
      default: return 'bg-purple-500';
    }
  };

  if (strategies.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg">
        <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">Strategy Comparison</h2>
        <p className="text-gray-600 dark:text-gray-400">Run optimization to see strategies...</p>
      </div>
    );
  }

  const optimal = strategies.find(s => s.tag === 'OPTIMAL');
  const variable = strategies.find(s => s.tag === 'VARIABLE');
  const others = strategies.filter(s => s.tag !== 'OPTIMAL' && s.tag !== 'VARIABLE');

  const renderCard = (strategy: Strategy, label: string, borderColor: string, bgClass: string, labelColor: string, labelBg: string) => (
    <div className={`p-4 rounded-lg ${bgClass} border-2`} style={{ borderColor }}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-bold text-gray-900 dark:text-white">{label}</h3>
        <span className={`text-xs font-bold px-2 py-1 rounded ${labelColor} ${labelBg}`}>
          {strategy.tag}
        </span>
      </div>
      <div className="space-y-2 text-sm">
        <div>
          <span className="text-gray-600 dark:text-gray-400">Stops:</span>
          <span className="ml-2 font-semibold text-gray-900 dark:text-white">{strategy.stops.length}</span>
        </div>
        <div>
          <span className="text-gray-600 dark:text-gray-400">Pit Laps:</span>
          <div className="mt-1 flex flex-wrap gap-1">
            {strategy.stops.map((stop, i) => (
              <span key={i} className={`${getCompoundColor(stop.compound)} text-white px-2 py-1 rounded text-xs font-medium`}>
                L{stop.lap} → {stop.compound}
              </span>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2 pt-1">
          <div>
            <span className="text-gray-500 dark:text-gray-400 text-xs block">Mean Time</span>
            <span className="font-mono font-bold text-gray-900 dark:text-white">{formatTime(strategy.total_race_time_seconds)}</span>
          </div>
          <div>
            <span className="text-gray-500 dark:text-gray-400 text-xs block">P50 Time</span>
            <span className="font-mono font-bold text-gray-900 dark:text-white">{formatTime(strategy.p50_time)}</span>
          </div>
          <div>
            <span className="text-gray-500 dark:text-gray-400 text-xs block">P90 Time</span>
            <span className="font-mono text-gray-900 dark:text-white">{formatTime(strategy.p90_time)}</span>
          </div>
          <div>
            <span className="text-gray-500 dark:text-gray-400 text-xs block">Robustness</span>
            <span className="font-mono font-bold text-gray-900 dark:text-white">{strategy.robustness_score.toFixed(1)}/100</span>
          </div>
        </div>
        <div>
          <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-3 relative overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${strategy.robustness_score}%`,
                background: `linear-gradient(to right, #ef4444, #f59e0b, #10b981)`,
              }}
            />
            <span className="absolute inset-0 flex items-center justify-center text-[10px] font-bold text-gray-900">
              {strategy.robustness_score.toFixed(1)}/100
            </span>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg">
      <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">Strategy Comparison</h2>
      
      {/* Two Hero Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {optimal && renderCard(
          optimal,
          'Best in Optimal Conditions',
          '#10b981',
          'bg-green-50 dark:bg-green-900/20',
          'text-green-600 dark:text-green-400',
          'bg-green-100 dark:bg-green-900/50',
        )}
        {variable && renderCard(
          variable,
          'Best in Variable Conditions',
          '#f59e0b',
          'bg-amber-50 dark:bg-amber-900/20',
          'text-amber-600 dark:text-amber-400',
          'bg-amber-100 dark:bg-amber-900/50',
        )}
      </div>

      {/* Remaining Strategies Table */}
      {others.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wider">
            All {strategies.length} Strategies
          </h3>
          <div className="max-h-96 overflow-y-auto border border-gray-200 dark:border-gray-700 rounded-lg">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-700 sticky top-0">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">#</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Stops</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Pit Plan</th>
                  <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">P50</th>
                  <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">P90</th>
                  <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Rob.</th>
                  <th className="px-3 py-2 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Tag</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {strategies.map((strategy, idx) => {
                  const isOptimal = strategy.tag === 'OPTIMAL';
                  const isVariable = strategy.tag === 'VARIABLE';
                  const rowBg = isOptimal
                    ? 'bg-green-50/50 dark:bg-green-900/10'
                    : isVariable
                    ? 'bg-amber-50/50 dark:bg-amber-900/10'
                    : '';
                  return (
                    <tr key={idx} className={`${rowBg} hover:bg-gray-50 dark:hover:bg-gray-700/50`}>
                      <td className="px-3 py-2 text-gray-600 dark:text-gray-400 font-mono">{idx + 1}</td>
                      <td className="px-3 py-2 text-gray-900 dark:text-white font-semibold">{strategy.stops.length}</td>
                      <td className="px-3 py-2">
                        <div className="flex flex-wrap gap-1">
                          {strategy.stops.map((stop, i) => (
                            <span key={i} className={`${getCompoundColor(stop.compound)} text-white px-1.5 py-0.5 rounded text-[10px] font-medium`}>
                              L{stop.lap}→{stop.compound.slice(0, 3)}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="px-3 py-2 text-right font-mono text-gray-900 dark:text-white">{formatTime(strategy.p50_time)}</td>
                      <td className="px-3 py-2 text-right font-mono text-gray-900 dark:text-white">{formatTime(strategy.p90_time)}</td>
                      <td className="px-3 py-2 text-right font-mono text-gray-900 dark:text-white">{strategy.robustness_score.toFixed(1)}</td>
                      <td className="px-3 py-2 text-center">
                        {isOptimal && (
                          <span className="text-[10px] font-bold text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/50 px-1.5 py-0.5 rounded">
                            OPTIMAL
                          </span>
                        )}
                        {isVariable && (
                          <span className="text-[10px] font-bold text-amber-600 dark:text-amber-400 bg-amber-100 dark:bg-amber-900/50 px-1.5 py-0.5 rounded">
                            VARIABLE
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
