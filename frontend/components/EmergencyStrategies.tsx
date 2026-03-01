'use client';

import type { EmergencyPitAdvice } from '@/lib/api';

interface EmergencyStrategiesProps {
  advice: EmergencyPitAdvice[] | null | undefined;
}

const compoundColors: Record<string, string> = {
  SOFT: 'bg-red-500/20 text-red-300 border-red-500/50',
  MEDIUM: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/50',
  HARD: 'bg-slate-400/20 text-slate-300 border-slate-400/50',
};

export default function EmergencyStrategies({ advice }: EmergencyStrategiesProps) {
  if (!advice?.length) return null;

  return (
    <div className="bg-gray-900 p-6 rounded-lg shadow-lg border border-amber-700/50">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-amber-400 text-lg" aria-hidden>⚠</span>
        <h3 className="text-sm font-mono text-amber-400 uppercase tracking-wider">
          Emergency / contingency pit strategies
        </h3>
      </div>
      <p className="text-gray-400 text-xs mb-4">
        If you have to pit between your recommended stops (safety car, puncture, damage), use these windows.
      </p>
      <ul className="space-y-3">
        {advice.map((item, i) => (
          <li
            key={i}
            className="flex flex-col gap-1 p-3 rounded-md bg-gray-800/60 border border-gray-700"
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-amber-300 text-sm">
                Laps {item.lap_range}
              </span>
              <span
                className={`px-2 py-0.5 rounded text-xs font-semibold border ${
                  compoundColors[item.compound] ?? 'bg-gray-600 text-gray-300 border-gray-500'
                }`}
              >
                {item.compound}
              </span>
            </div>
            <p className="text-gray-500 text-xs">{item.scenario}</p>
            <p className="text-green-400 font-mono text-sm mt-1">{item.summary}</p>
            {item.compound_if_rain && item.summary_if_rain && (
              <div className="mt-2 pt-2 border-t border-gray-600">
                <span className="text-cyan-400 text-xs font-mono">If raining: </span>
                <span
                  className={`inline-block px-2 py-0.5 rounded text-xs font-semibold border mr-1 ${
                    compoundColors[item.compound_if_rain] ?? 'bg-gray-600 text-gray-300 border-gray-500'
                  }`}
                >
                  {item.compound_if_rain}
                </span>
                <p className="text-cyan-300/90 font-mono text-xs mt-1">{item.summary_if_rain}</p>
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
