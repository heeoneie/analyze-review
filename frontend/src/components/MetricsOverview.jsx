import { FileText, ThumbsDown, Percent, Tag } from 'lucide-react';

const cards = [
  { key: 'total', label: '총 리뷰 수', icon: FileText, color: 'text-blue-600', bg: 'bg-blue-50' },
  { key: 'negative', label: '부정 리뷰 수', icon: ThumbsDown, color: 'text-red-600', bg: 'bg-red-50' },
  { key: 'ratio', label: '부정 비율', icon: Percent, color: 'text-orange-600', bg: 'bg-orange-50' },
  { key: 'categories', label: '발견된 카테고리', icon: Tag, color: 'text-purple-600', bg: 'bg-purple-50' },
];

export default function MetricsOverview({ stats, categoryCount }) {
  const values = {
    total: stats.total_reviews?.toLocaleString(),
    negative: stats.negative_reviews?.toLocaleString(),
    ratio: `${stats.negative_ratio}%`,
    categories: categoryCount,
  };

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {cards.map(({ key, label, icon: Icon, color, bg }) => (
        <div key={key} className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
          <div className="flex items-center gap-3">
            <div className={`${bg} p-2.5 rounded-xl`}>
              <Icon className={color} size={20} />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{values[key]}</p>
              <p className="text-xs text-gray-500 mt-0.5">{label}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
