import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { getCategoryLabel } from '../constants/categoryLabels';

const COLORS = [
  '#3b82f6', '#ef4444', '#f59e0b', '#10b981', '#8b5cf6',
  '#ec4899', '#06b6d4', '#f97316', '#6366f1', '#14b8a6',
  '#e11d48', '#84cc16', '#0ea5e9', '#d946ef', '#64748b',
  '#facc15', '#a855f7',
];

export default function CategoryChart({ allCategories }) {
  const chartData = Object.entries(allCategories || {})
    .map(([name, value]) => ({ name, label: getCategoryLabel(name), value }))
    .sort((a, b) => b.value - a.value);

  const top5 = chartData.slice(0, 5);
  const otherSum = chartData.slice(5).reduce((acc, d) => acc + d.value, 0);
  const pieData = otherSum > 0 ? [...top5, { name: 'others', label: '기타', value: otherSum }] : top5;

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
      <h3 className="text-lg font-bold text-gray-900 mb-4">카테고리별 분포</h3>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 도넛 차트 */}
        <div>
          <p className="text-sm text-gray-500 mb-2 font-medium">상위 카테고리</p>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={85}
                dataKey="value"
                label={({ label, percent }) => `${label} ${(percent * 100).toFixed(0)}%`}
                labelLine={true}
                fontSize={11}
              >
                {pieData.map((_, idx) => (
                  <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(value, name, props) => [value + '건', props.payload.label]} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* 바 차트 */}
        <div>
          <p className="text-sm text-gray-500 mb-2 font-medium">전체 카테고리 빈도</p>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chartData} layout="vertical" margin={{ left: 80 }}>
              <XAxis type="number" />
              <YAxis type="category" dataKey="label" tick={{ fontSize: 11 }} width={80} />
              <Tooltip formatter={(value) => [value + '건', '빈도']} />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                {chartData.map((_, idx) => (
                  <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
