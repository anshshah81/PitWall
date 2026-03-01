'use client';

interface AIBriefProps {
  brief: string;
}

export default function AIBrief({ brief }: AIBriefProps) {
  return (
    <div className="bg-gray-900 p-6 rounded-lg shadow-lg border border-gray-700">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
        <h3 className="text-xs font-mono text-gray-400 uppercase tracking-wider">
          Race Engineer - Team Radio
        </h3>
      </div>
      <p className="font-mono text-green-400 text-sm leading-relaxed">
        {brief || 'Waiting for optimization...'}
      </p>
    </div>
  );
}
