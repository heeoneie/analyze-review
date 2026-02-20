import { Network, Loader2, ChevronDown } from 'lucide-react';

const TYPE_CFG = {
  channel:    { label: '감지 채널',     color: '#10B981', bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-700', ring: 'ring-emerald-300' },
  category:   { label: '이슈 카테고리', color: '#EF4444', bg: 'bg-red-50',     border: 'border-red-200',     text: 'text-red-700',     ring: 'ring-red-300' },
  root_cause: { label: '근본 원인',     color: '#F97316', bg: 'bg-orange-50',  border: 'border-orange-200',  text: 'text-orange-700',  ring: 'ring-orange-300' },
  department: { label: '담당 부서',     color: '#3B82F6', bg: 'bg-blue-50',    border: 'border-blue-200',    text: 'text-blue-700',    ring: 'ring-blue-300' },
  risk_type:  { label: '리스크 유형',   color: '#8B5CF6', bg: 'bg-purple-50',  border: 'border-purple-200',  text: 'text-purple-700',  ring: 'ring-purple-300' },
};

const TYPE_ORDER = ['channel', 'category', 'root_cause', 'department', 'risk_type'];

function NodeChip({ node, cfg }) {
  const severity = node.severity || 0;
  const isHigh = severity >= 9;
  const isMed  = severity >= 7 && severity < 9;
  return (
    <div
      className={[
        'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm',
        cfg.bg, cfg.border,
        isHigh ? `ring-2 ${cfg.ring}` : '',
      ].join(' ')}
    >
      <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: cfg.color }} />
      <span className={`font-semibold ${cfg.text}`}>{node.label}</span>
      {isHigh && (
        <span className="ml-0.5 text-xs bg-red-500 text-white px-1.5 py-0.5 rounded-full font-bold leading-none">
          {severity}
        </span>
      )}
      {isMed && (
        <span className="ml-0.5 text-xs bg-orange-400 text-white px-1.5 py-0.5 rounded-full font-bold leading-none">
          {severity}
        </span>
      )}
    </div>
  );
}

export default function OntologyGraph({ data, loading, error, onGenerate }) {
  const grouped = {};
  if (data?.nodes) {
    for (const node of data.nodes) {
      const t = node.type || 'category';
      if (!grouped[t]) grouped[t] = [];
      grouped[t].push(node);
    }
    for (const t of Object.keys(grouped)) {
      grouped[t].sort((a, b) => (b.severity || 0) - (a.severity || 0));
    }
  }

  const visibleTypes = TYPE_ORDER.filter((t) => grouped[t]?.length > 0);

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Network className="text-purple-500" size={20} />
          <h3 className="text-lg font-bold text-gray-900">리스크 온톨로지 그래프</h3>
        </div>
        {!data && !loading && (
          <button
            onClick={onGenerate}
            className="px-4 py-2 text-sm bg-purple-50 text-purple-600 rounded-lg hover:bg-purple-100 transition-colors"
          >
            온톨로지 생성
          </button>
        )}
      </div>

      {error && (
        <div className="bg-red-50 text-red-600 rounded-lg px-4 py-2 text-sm mb-4">{error}</div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-48 text-gray-400">
          <Loader2 className="animate-spin mr-2" size={20} />
          온톨로지 그래프 생성 중...
        </div>
      ) : data ? (
        <div className="space-y-1">
          {/* Legend */}
          <div className="flex flex-wrap gap-3 mb-4">
            {Object.entries(TYPE_CFG).map(([type, cfg]) => (
              <div key={type} className="flex items-center gap-1.5 text-xs text-gray-600">
                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: cfg.color }} />
                {cfg.label}
              </div>
            ))}
            <span className="ml-2 border-l pl-3 text-xs text-gray-400 flex items-center gap-1">
              <span className="bg-red-500 text-white px-1.5 rounded-full font-bold">9+</span>
              고위험
            </span>
          </div>

          {/* Hierarchy rows */}
          <div className="bg-gray-50 rounded-xl p-5 space-y-0.5">
            {visibleTypes.map((type, idx) => {
              const cfg = TYPE_CFG[type];
              const nodes = grouped[type];
              const showArrow = idx < visibleTypes.length - 1;
              return (
                <div key={type}>
                  <div className="flex items-start gap-4 py-2">
                    {/* Type label */}
                    <div className="flex-shrink-0 w-28 pt-1.5 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <span className="w-2 h-2 rounded-full" style={{ backgroundColor: cfg.color }} />
                        <span className="text-xs font-semibold text-gray-500">{cfg.label}</span>
                      </div>
                    </div>
                    {/* Divider */}
                    <div className="flex-shrink-0 w-px bg-gray-200 self-stretch my-0.5" />
                    {/* Chips */}
                    <div className="flex flex-wrap gap-2 flex-1">
                      {nodes.map((node) => (
                        <NodeChip key={node.id} node={node} cfg={cfg} />
                      ))}
                    </div>
                  </div>
                  {showArrow && (
                    <div className="ml-32 pl-5 py-0.5">
                      <ChevronDown className="text-gray-300" size={16} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Summary */}
          {data.summary && (
            <p className="mt-3 text-sm text-gray-600 bg-purple-50 rounded-lg p-3 leading-relaxed">
              {data.summary}
            </p>
          )}
          <p className="text-xs text-gray-400 text-right pt-1">
            노드 {data.nodes?.length || 0}개 · 관계 {data.links?.length || 0}개
          </p>
        </div>
      ) : (
        <div className="flex items-center justify-center h-48 text-gray-300 text-sm">
          &quot;전체 리스크 분석 실행&quot; 또는 &quot;온톨로지 생성&quot; 버튼을 클릭하세요
        </div>
      )}
    </div>
  );
}
