import { Network, Loader2 } from 'lucide-react';

const LX  = [14, 214, 414, 614];
const NW  = 120;
const NH  = 34;
const SW  = 782;
const SH  = 350;

const LCFG = [
  { label: '감지 채널',   color: '#34D399' },
  { label: '리스크 사건', color: '#FB923C' },
  { label: '경영 타격',   color: '#F87171' },
  { label: '대응 주체',   color: '#818CF8' },
];

const GNODES = [
  { id: 's1', layer: 0, label: '유튜브 불만댓글',  y: 30  },
  { id: 's2', layer: 0, label: '트위터 바이럴',    y: 118 },
  { id: 's3', layer: 0, label: '커뮤니티 확산',    y: 206 },
  { id: 's4', layer: 0, label: '언론 기사 포착',   y: 294 },
  { id: 'e1', layer: 1, label: '제품 결함 논란',   y: 74  },
  { id: 'e2', layer: 1, label: '환불 분쟁 급증',   y: 162 },
  { id: 'e3', layer: 1, label: '브랜드 신뢰 붕괴', y: 250 },
  { id: 'i1', layer: 2, label: '매출 급락',        y: 30  },
  { id: 'i2', layer: 2, label: '법적 리스크',      y: 118 },
  { id: 'i3', layer: 2, label: '주가 하락',        y: 206 },
  { id: 'i4', layer: 2, label: '파트너 이탈',      y: 294 },
  { id: 'a1', layer: 3, label: '경영진 긴급대응',  y: 30  },
  { id: 'a2', layer: 3, label: '법무팀',           y: 118 },
  { id: 'a3', layer: 3, label: 'PR팀',             y: 206 },
  { id: 'a4', layer: 3, label: 'CS팀 대응',        y: 294 },
];

const GEDGES = [
  { from: 's1', to: 'e1' },
  { from: 's1', to: 'e3' },
  { from: 's2', to: 'e1' },
  { from: 's2', to: 'e3' },
  { from: 's3', to: 'e2' },
  { from: 's3', to: 'e3' },
  { from: 's4', to: 'e3' },
  { from: 'e1', to: 'i1' },
  { from: 'e1', to: 'i2' },
  { from: 'e2', to: 'i1' },
  { from: 'e2', to: 'i2' },
  { from: 'e3', to: 'i3' },
  { from: 'e3', to: 'i4' },
  { from: 'i1', to: 'a1', thick: true },
  { from: 'i1', to: 'a4'              },
  { from: 'i2', to: 'a2'              },
  { from: 'i2', to: 'a3'              },
  { from: 'i3', to: 'a1', thick: true },
  { from: 'i4', to: 'a3'              },
];

function epath(fn, tn) {
  const x1 = LX[fn.layer] + NW;
  const y1 = fn.y + NH / 2;
  const x2 = LX[tn.layer];
  const y2 = tn.y + NH / 2;
  const c  = (x2 - x1) * 0.45;
  return `M ${x1} ${y1} C ${x1 + c} ${y1}, ${x2 - c} ${y2}, ${x2} ${y2}`;
}

function DAGGraph() {
  const nm = Object.fromEntries(GNODES.map((n) => [n.id, n]));
  return (
    <svg viewBox={`0 0 ${SW} ${SH}`} width="100%" style={{ minWidth: 480 }}>
      <defs>
        <marker id="dag-a" markerWidth="8" markerHeight="8"
          refX="7" refY="3" orient="auto">
          <path d="M0,0 L0,6 L8,3 z" fill="#475569" />
        </marker>
        <marker id="dag-ar" markerWidth="8" markerHeight="8"
          refX="7" refY="3" orient="auto">
          <path d="M0,0 L0,6 L8,3 z" fill="#F87171" />
        </marker>
      </defs>

      {/* layer headers */}
      {LCFG.map((cfg, i) => (
        <g key={i}>
          <rect
            x={LX[i]} y={0} width={NW} height={22} rx={5}
            fill={cfg.color} fillOpacity={0.12}
            stroke={cfg.color} strokeWidth={1} strokeOpacity={0.35}
          />
          <text
            x={LX[i] + NW / 2} y={14}
            textAnchor="middle" fontSize={10} fontWeight="700" fill={cfg.color}
          >
            {cfg.label}
          </text>
        </g>
      ))}

      {/* edges — rendered before nodes so they appear behind */}
      {GEDGES.map((e, i) => (
        <path
          key={i}
          d={epath(nm[e.from], nm[e.to])}
          fill="none"
          stroke={e.thick ? '#F87171' : '#334155'}
          strokeWidth={e.thick ? 2 : 1}
          strokeOpacity={e.thick ? 0.9 : 0.55}
          markerEnd={e.thick ? 'url(#dag-ar)' : 'url(#dag-a)'}
        />
      ))}

      {/* nodes */}
      {GNODES.map((n) => {
        const cfg = LCFG[n.layer];
        return (
          <g key={n.id}>
            <rect
              x={LX[n.layer]} y={n.y} width={NW} height={NH} rx={6}
              fill="#0f172a"
              stroke={cfg.color} strokeWidth={1.5} strokeOpacity={0.65}
            />
            <text
              x={LX[n.layer] + NW / 2}
              y={n.y + NH / 2}
              textAnchor="middle"
              dominantBaseline="central"
              fontSize={10.5}
              fontWeight="500"
              fill="#cbd5e1"
            >
              {n.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export default function OntologyGraph({ data, loading, error }) {
  return (
    <div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-6">
      <div className="flex items-center gap-2 mb-5">
        <Network className="text-zinc-400" size={18} />
        <h3 className="text-base font-bold text-white">리스크 인과 관계 DAG</h3>
        {loading && (
          <span className="flex items-center gap-1 text-xs text-zinc-500 ml-1">
            <Loader2 className="animate-spin" size={12} />
            분석 중...
          </span>
        )}
      </div>

      {error && (
        <div className="bg-red-950 text-red-400 border border-red-800 rounded-lg px-4 py-2 text-sm mb-4">
          {error}
        </div>
      )}

      <DAGGraph />

      {/* legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-3 px-1">
        {LCFG.map((cfg, i) => (
          <div key={i} className="flex items-center gap-1.5 text-xs text-zinc-500">
            <span className="w-2 h-2 rounded-sm flex-shrink-0" style={{ backgroundColor: cfg.color }} />
            {cfg.label}
          </div>
        ))}
        <div className="flex items-center gap-1.5 text-xs text-zinc-500 ml-2 border-l border-zinc-700 pl-3">
          <span className="inline-block w-5 h-0.5 flex-shrink-0" style={{ background: '#F87171' }} />
          경영진 직접 에스컬레이션
        </div>
      </div>

      {data?.summary && (
        <p className="mt-3 text-sm text-zinc-400 bg-zinc-800 border border-zinc-700 rounded-lg p-3 leading-relaxed">
          {data.summary}
        </p>
      )}
    </div>
  );
}
