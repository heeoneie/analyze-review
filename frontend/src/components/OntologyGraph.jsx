import { Network, Loader2, ChevronDown } from 'lucide-react';

const TYPE_CFG = {
  channel:    { label: '감지 채널',     color: '#34D399' },
  category:   { label: '이슈 카테고리', color: '#F87171' },
  root_cause: { label: '근본 원인',     color: '#FB923C' },
  department: { label: '담당 부서',     color: '#60A5FA' },
  risk_type:  { label: '리스크 유형',   color: '#A78BFA' },
};

const TYPE_ORDER = ['channel', 'category', 'root_cause', 'department', 'risk_type'];

function NodeChip({ node, cfg }) {
  const severity = node.severity || 0;
  const isHigh = severity >= 9;
  const isMed  = severity >= 7 && severity < 9;
  return (
    <div className={[
      'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs',
      'bg-slate-800 border-slate-700',
      isHigh ? 'border-red-700 ring-1 ring-red-800' : '',
    ].join(' ')}>
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: cfg.color }} />
      <span className="font-medium text-slate-200">{node.label}</span>
      {isHigh && (
        <span className="ml-0.5 text-[10px] bg-red-900 text-red-400 border border-red-700 px-1.5 py-px rounded-full font-bold leading-none">
          {severity}
        </span>
      )}
      {isMed && (
        <span className="ml-0.5 text-[10px] bg-amber-950 text-amber-400 border border-amber-800 px-1.5 py-px rounded-full font-bold leading-none">
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
    <div className="bg-slate-900 rounded-2xl border border-slate-800 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Network className="text-slate-400" size={18} />
          <h3 className="text-base font-bold text-white">리스크 온톨로지 그래프</h3>
        </div>
        {!data && !loading && (
          <button
            onClick={onGenerate}
            className="px-3 py-1.5 text-sm bg-slate-800 text-slate-300 rounded-lg hover:bg-slate-700 transition-colors border border-slate-700"
          >
            온톨로지 생성
          </button>
        )}
      </div>

      {error && (
        <div className="bg-red-950 text-red-400 border border-red-800 rounded-lg px-4 py-2 text-sm mb-4">{error}</div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-48 text-slate-500">
          <Loader2 className="animate-spin mr-2" size={20} />
          온톨로지 그래프 생성 중...
        </div>
      ) : data ? (
        <div className="space-y-1">
          {/* Legend */}
          <div className="flex flex-wrap gap-3 mb-4">
            {Object.entries(TYPE_CFG).map(([type, cfg]) => (
              <div key={type} className="flex items-center gap-1.5 text-xs text-slate-500">
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: cfg.color }} />
                {cfg.label}
              </div>
            ))}
            <span className="ml-2 border-l border-slate-700 pl-3 text-xs text-slate-600 flex items-center gap-1">
              <span className="bg-red-900 text-red-400 border border-red-700 px-1.5 rounded-full font-bold text-[10px]">9+</span>
              고위험
            </span>
          </div>

          {/* Hierarchy rows */}
          <div className="bg-slate-800/50 rounded-xl p-5 border border-slate-700 space-y-0.5">
            {visibleTypes.map((type, idx) => {
              const cfg = TYPE_CFG[type];
              const nodes = grouped[type];
              const showArrow = idx < visibleTypes.length - 1;
              return (
                <div key={type}>
                  <div className="flex items-start gap-4 py-2">
                    <div className="flex-shrink-0 w-28 pt-1.5 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: cfg.color }} />
                        <span className="text-xs font-medium text-slate-500">{cfg.label}</span>
                      </div>
                    </div>
                    <div className="flex-shrink-0 w-px bg-slate-700 self-stretch my-0.5" />
                    <div className="flex flex-wrap gap-1.5 flex-1">
                      {nodes.map((node) => (
                        <NodeChip key={node.id} node={node} cfg={cfg} />
                      ))}
                    </div>
                  </div>
                  {showArrow && (
                    <div className="ml-32 pl-5 py-0.5">
                      <ChevronDown className="text-slate-700" size={14} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Summary */}
          {data.summary && (
            <p className="mt-3 text-sm text-slate-400 bg-slate-800 border border-slate-700 rounded-lg p-3 leading-relaxed">
              {data.summary}
            </p>
          )}
          <p className="text-xs text-slate-600 text-right pt-1">
            노드 {data.nodes?.length || 0}개 · 관계 {data.links?.length || 0}개
          </p>
        </div>
      ) : (
        <div className="flex items-center justify-center h-48 text-slate-600 text-sm">
          &quot;전체 리스크 분석 실행&quot; 또는 &quot;온톨로지 생성&quot; 버튼을 클릭하세요
        </div>
      )}
    </div>
  );
}
