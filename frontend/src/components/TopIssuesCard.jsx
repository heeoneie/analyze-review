import { AlertTriangle } from 'lucide-react';

const CATEGORY_LABELS = {
  battery_issue: '배터리 문제',
  network_issue: '네트워크 문제',
  display_issue: '화면 문제',
  software_issue: '소프트웨어 문제',
  overheating: '발열',
  sound_issue: '사운드 문제',
  delivery_delay: '배송 지연',
  wrong_item: '오배송',
  poor_quality: '품질 불량',
  damaged_packaging: '포장 파손',
  size_issue: '크기 불만',
  missing_parts: '구성품 누락',
  not_as_described: '상품 불일치',
  customer_service: '고객 서비스',
  price_issue: '가격 불만',
  positive_review: '긍정 리뷰',
  other: '기타',
};

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
        {topIssues.map((issue, idx) => (
          <div
            key={issue.category}
            className={`border-l-4 rounded-xl p-4 ${RANK_COLORS[idx] || 'border-gray-300 bg-gray-50'}`}
          >
            <div className="flex items-center gap-3 mb-2">
              <span className={`${RANK_BADGE[idx] || 'bg-gray-500'} text-white text-xs font-bold px-2 py-0.5 rounded-full`}>
                {idx + 1}위
              </span>
              <span className="font-bold text-gray-900">
                {CATEGORY_LABELS[issue.category] || issue.category}
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
