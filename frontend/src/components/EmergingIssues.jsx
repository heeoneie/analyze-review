import { TrendingUp, CheckCircle } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

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

export default function EmergingIssues({ emergingIssues }) {
  if (!emergingIssues || emergingIssues.length === 0) {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="text-green-500" size={20} />
          <h3 className="text-lg font-bold text-gray-900">급증 이슈</h3>
        </div>
        <div className="flex items-center gap-2 text-green-600 bg-green-50 rounded-xl p-4">
          <CheckCircle size={20} />
          <p className="font-medium">급증하는 이슈가 없습니다. 안정적인 상태입니다.</p>
        </div>
      </div>
    );
  }

  const chartData = emergingIssues.map((issue) => ({
    name: CATEGORY_LABELS[issue.category] || issue.category,
    증가율: issue.increase_rate,
    이전: issue.comparison_count,
    최근: issue.recent_count,
  }));

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
      <div className="flex items-center gap-2 mb-4">
        <TrendingUp className="text-red-500" size={20} />
        <h3 className="text-lg font-bold text-gray-900">급증 이슈</h3>
      </div>

      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={chartData} margin={{ left: 20 }}>
          <XAxis dataKey="name" tick={{ fontSize: 12 }} />
          <YAxis label={{ value: '증가율 (%)', angle: -90, position: 'insideLeft', fontSize: 11 }} />
          <Tooltip formatter={(value, name) => [name === '증가율' ? `+${value}%` : `${value}건`, name]} />
          <Bar dataKey="증가율" radius={[4, 4, 0, 0]}>
            {chartData.map((_, idx) => (
              <Cell key={idx} fill={idx === 0 ? '#ef4444' : idx === 1 ? '#f97316' : '#fbbf24'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div className="mt-4 space-y-2">
        {emergingIssues.map((issue) => (
          <div key={issue.category} className="flex items-center justify-between text-sm bg-red-50 rounded-lg px-4 py-2">
            <span className="font-medium text-gray-700">
              {CATEGORY_LABELS[issue.category] || issue.category}
            </span>
            <span className="text-red-600 font-bold">
              {issue.comparison_count}건 → {issue.recent_count}건 (+{issue.increase_rate}%)
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
