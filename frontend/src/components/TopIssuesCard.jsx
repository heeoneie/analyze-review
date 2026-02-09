import { AlertTriangle } from 'lucide-react';
import { getCategoryLabel } from '../constants/categoryLabels';

const RANK_COLORS = [
  'border-red-500 bg-red-50',
  'border-orange-500 bg-orange-50',
  'border-yellow-500 bg-yellow-50',
];

const RANK_BADGE = [
  'bg-red-500',
  'bg-orange-500',
  'bg-yellow-500',
];

export default function TopIssuesCard({ topIssues }) {
  if (!topIssues || topIssues.length === 0) return null;

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
      <div className="flex items-center gap-2 mb-4">
        <AlertTriangle className="text-red-500" size={20} />
        <h3 className="text-lg font-bold text-gray-900">Top 3 부정 이슈</h3>
      </div>

      <div className="space-y-3">
        {topIssues.slice(0, 3).map((issue, idx) => (
          <div
            key={issue.category}
            className={`border-l-4 rounded-xl p-4 ${RANK_COLORS[idx] || 'border-gray-300 bg-gray-50'}`}
          >
            <div className="flex items-center gap-3 mb-2">
              <span className={`${RANK_BADGE[idx] || 'bg-gray-500'} text-white text-xs font-bold px-2 py-0.5 rounded-full`}>
                {idx + 1}위
              </span>
              <span className="font-bold text-gray-900">
                {getCategoryLabel(issue.category)}
              </span>
              <span className="text-sm text-gray-500 ml-auto">
                {issue.count}건 ({issue.percentage}%)
              </span>
            </div>
            <div className="space-y-1">
              {issue.examples?.slice(0, 3).map((ex, i) => (
                <p key={i} className="text-sm text-gray-600 pl-2 border-l-2 border-gray-200">
                  "{ex}"
                </p>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
