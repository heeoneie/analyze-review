import { Network, Loader2 } from 'lucide-react';
import { useLang } from '../contexts/LangContext';

const LX  = [14, 214, 414, 614];
const NW  = 120;
const NH  = 34;
const SW  = 782;
const SH  = 350;

const LCFG_KEYS = [
  { labelKey: 'ontology.lcfg0', color: '#34D399' },
  { labelKey: 'ontology.lcfg1', color: '#FB923C' },
  { labelKey: 'ontology.lcfg2', color: '#F87171' },
  { labelKey: 'ontology.lcfg3', color: '#818CF8' },
];

const GNODES = [
  { id: 's1', layer: 0, labelKey: 'ontology.n_s1', y: 30  },
  { id: 's2', layer: 0, labelKey: 'ontology.n_s2', y: 118 },
  { id: 's3', layer: 0, labelKey: 'ontology.n_s3', y: 206 },
  { id: 's4', layer: 0, labelKey: 'ontology.n_s4', y: 294 },
  { id: 'e1', layer: 1, labelKey: 'ontology.n_e1', y: 74  },
  { id: 'e2', layer: 1, labelKey: 'ontology.n_e2', y: 162 },
  { id: 'e3', layer: 1, labelKey: 'ontology.n_e3', y: 250 },
  { id: 'i1', layer: 2, labelKey: 'ontology.n_i1', y: 30  },
  { id: 'i2', layer: 2, labelKey: 'ontology.n_i2', y: 118 },
  { id: 'i3', layer: 2, labelKey: 'ontology.n_i3', y: 206 },
  { id: 'i4', layer: 2, labelKey: 'ontology.n_i4', y: 294 },
  { id: 'a1', layer: 3, labelKey: 'ontology.n_a1', y: 30  },
  { id: 'a2', layer: 3, labelKey: 'ontology.n_a2', y: 118 },
  { id: 'a3', layer: 3, labelKey: 'ontology.n_a3', y: 206 },
  { id: 'a4', layer: 3, labelKey: 'ontology.n_a4', y: 294 },
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
  const { t } = useLang();
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
      {LCFG_KEYS.map((cfg, i) => (
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
            {t(cfg.labelKey)}
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
        const cfg = LCFG_KEYS[n.layer];
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
              {t(n.labelKey)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export default function OntologyGraph({ data, loading, error }) {
  const { t } = useLang();
  return (
    <div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-6">
      <div className="flex items-center gap-2 mb-5">
        <Network className="text-zinc-400" size={18} />
        <h3 className="text-base font-bold text-white">{t('ontology.title')}</h3>
        {loading && (
          <span className="flex items-center gap-1 text-xs text-zinc-500 ml-1">
            <Loader2 className="animate-spin" size={12} />
            {t('ontology.analyzing')}
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
        {LCFG_KEYS.map((cfg, i) => (
          <div key={i} className="flex items-center gap-1.5 text-xs text-zinc-500">
            <span className="w-2 h-2 rounded-sm flex-shrink-0" style={{ backgroundColor: cfg.color }} />
            {t(cfg.labelKey)}
          </div>
        ))}
        <div className="flex items-center gap-1.5 text-xs text-zinc-500 ml-2 border-l border-zinc-700 pl-3">
          <span className="inline-block w-5 h-0.5 flex-shrink-0" style={{ background: '#F87171' }} />
          {t('ontology.escalation')}
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
