import { Lightbulb } from 'lucide-react';

// 백엔드는 {title, problem, action, expected_impact} 객체 배열을 돌려준다.
// 예전에는 문자열 배열이었어서, 둘 다 받아 준다.
function Recommendation({ rec }) {
  if (typeof rec === 'string') {
    return <p className="text-gray-800 leading-relaxed">{rec}</p>;
  }

  return (
    <div className="space-y-1.5">
      {rec.title && <p className="font-semibold text-gray-900">{rec.title}</p>}
      {rec.problem && (
        <p className="text-sm text-gray-600">
          <span className="font-medium text-gray-500">대응 문제 </span>
          {rec.problem}
        </p>
      )}
      {rec.action && (
        <p className="text-sm text-gray-800 leading-relaxed">
          <span className="font-medium text-gray-500">실행 </span>
          {rec.action}
        </p>
      )}
      {rec.expected_impact && (
        <p className="text-sm text-gray-600">
          <span className="font-medium text-gray-500">기대 효과 </span>
          {rec.expected_impact}
        </p>
      )}
    </div>
  );
}

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
            <div className="min-w-0 flex-1">
              <Recommendation rec={rec} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
