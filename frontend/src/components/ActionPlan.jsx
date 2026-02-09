import { Lightbulb } from 'lucide-react';

export default function ActionPlan({ recommendations }) {
  if (!recommendations || recommendations.length === 0) return null;

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
      <div className="flex items-center gap-2 mb-4">
        <Lightbulb className="text-yellow-500" size={20} />
        <h3 className="text-lg font-bold text-gray-900">AI 개선 액션</h3>
      </div>

      <div className="space-y-3">
        {recommendations.map((rec, idx) => (
          <div key={idx} className="flex gap-3 bg-blue-50 rounded-xl p-4">
            <div className="flex-shrink-0 w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center font-bold text-sm">
              {idx + 1}
            </div>
            <p className="text-gray-800 leading-relaxed">{rec}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
