'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';
import type { Strategy } from '@/lib/api';

interface StrategyChartProps {
  strategies: Strategy[];
  totalLaps: number;
}

// 20-color palette: two hero colors + 18 muted background colors
const HERO_OPTIMAL = '#10b981'; // bright green
const HERO_VARIABLE = '#f59e0b'; // bright amber
const BG_COLORS = [
  '#6b7280', '#9ca3af', '#64748b', '#78716c', '#737373',
  '#71717a', '#a1a1aa', '#a3a3a3', '#94a3b8', '#7c8594',
  '#8b8b8b', '#7e7e7e', '#8d99ae', '#6c757d', '#868e96',
  '#a0a0a0', '#8e8e8e', '#7a7a7a',
];

export default function StrategyChart({ strategies, totalLaps }: StrategyChartProps) {
  if (strategies.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg">
        <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">Strategy Visualization</h2>
        <p className="text-gray-600 dark:text-gray-400">Run optimization to see lap-by-lap analysis...</p>
      </div>
    );
  }

  // Find the OPTIMAL and VARIABLE strategies
  const optimalIdx = strategies.findIndex(s => s.tag === 'OPTIMAL');
  const variableIdx = strategies.findIndex(s => s.tag === 'VARIABLE');

  // Generate lap-by-lap data for all strategies
  const data = [];
  for (let lap = 1; lap <= totalLaps; lap++) {
    const point: Record<string, number> = { lap };
    strategies.forEach((strategy, idx) => {
      const delta = (strategy.total_race_time_seconds - strategies[0].total_race_time_seconds) * (lap / totalLaps);
      point[`s${idx}`] = parseFloat(delta.toFixed(3));
    });
    data.push(point);
  }

  // Collect pit laps from OPTIMAL and VARIABLE strategies for reference lines
  const allPitLaps = new Set<number>();
  if (optimalIdx >= 0) strategies[optimalIdx].stops.forEach(s => allPitLaps.add(s.lap));
  if (variableIdx >= 0) strategies[variableIdx].stops.forEach(s => allPitLaps.add(s.lap));

  // Build line descriptors
  const getLabel = (idx: number) => {
    const s = strategies[idx];
    const stops = s.stops.map(st => `L${st.lap}→${st.compound}`).join(', ');
    if (s.tag === 'OPTIMAL') return `OPTIMAL: ${stops}`;
    if (s.tag === 'VARIABLE') return `VARIABLE: ${stops}`;
    return `#${idx + 1}: ${stops}`;
  };

  const getColor = (idx: number) => {
    if (idx === optimalIdx) return HERO_OPTIMAL;
    if (idx === variableIdx) return HERO_VARIABLE;
    // Assign from muted palette
    let bgIdx = 0;
    for (let i = 0; i < idx; i++) {
      if (i !== optimalIdx && i !== variableIdx) bgIdx++;
    }
    return BG_COLORS[bgIdx % BG_COLORS.length];
  };

  const getWidth = (idx: number) => {
    if (idx === optimalIdx || idx === variableIdx) return 3;
    return 1;
  };

  const getOpacity = (idx: number) => {
    if (idx === optimalIdx || idx === variableIdx) return 1;
    return 0.35;
  };

  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg">
      <h2 className="text-2xl font-bold mb-2 text-gray-900 dark:text-white">Strategy Visualization</h2>
      <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
        Showing {strategies.length} strategies — cumulative time delta vs best strategy
      </div>
      <div className="flex gap-4 mb-4 text-xs">
        <span className="flex items-center gap-1">
          <span className="inline-block w-4 h-1 rounded" style={{ backgroundColor: HERO_OPTIMAL }} /> Best Optimal (P50)
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-4 h-1 rounded" style={{ backgroundColor: HERO_VARIABLE }} /> Best Variable (Robustness)
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-4 h-0.5 rounded bg-gray-400 opacity-50" /> Other strategies
        </span>
      </div>
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis 
            dataKey="lap" 
            label={{ value: 'Lap Number', position: 'insideBottom', offset: -5 }}
            stroke="#9ca3af"
          />
          <YAxis 
            label={{ value: 'Time Delta (s)', angle: -90, position: 'insideLeft' }}
            stroke="#9ca3af"
          />
          <Tooltip 
            contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', maxWidth: '400px' }}
            labelStyle={{ color: '#fff' }}
            formatter={(value: number, name: string) => {
              // name is like "s0", "s1", etc.
              const idx = parseInt(name.replace('s', ''));
              return [value.toFixed(2) + 's', getLabel(idx)];
            }}
          />
          
          {/* Reference lines for pit stops */}
          {Array.from(allPitLaps).map(lap => (
            <ReferenceLine 
              key={lap}
              x={lap} 
              stroke="#ef4444" 
              strokeDasharray="3 3"
              label={{ value: `Pit`, position: 'top', fill: '#ef4444', fontSize: 10 }}
            />
          ))}

          {/* Background strategies first (rendered below) */}
          {strategies.map((_, idx) => {
            if (idx === optimalIdx || idx === variableIdx) return null;
            return (
              <Line
                key={`s${idx}`}
                type="monotone"
                dataKey={`s${idx}`}
                stroke={getColor(idx)}
                strokeWidth={getWidth(idx)}
                strokeOpacity={getOpacity(idx)}
                dot={false}
                name={`s${idx}`}
                legendType="none"
              />
            );
          })}

          {/* VARIABLE strategy (highlighted) */}
          {variableIdx >= 0 && (
            <Line
              type="monotone"
              dataKey={`s${variableIdx}`}
              stroke={HERO_VARIABLE}
              strokeWidth={3}
              dot={false}
              name={`s${variableIdx}`}
              legendType="none"
            />
          )}

          {/* OPTIMAL strategy (highlighted, on top) */}
          {optimalIdx >= 0 && (
            <Line
              type="monotone"
              dataKey={`s${optimalIdx}`}
              stroke={HERO_OPTIMAL}
              strokeWidth={3}
              dot={false}
              name={`s${optimalIdx}`}
              legendType="none"
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
