import { useMemo } from 'react';
import { Network, Loader2 } from 'lucide-react';
import { useLang } from '../contexts/LangContext';

const NW  = 130;
const NH  = 34;
const COL_GAP = 200;
const ROW_GAP = 54;
const PAD_X = 14;
const PAD_Y = 32;

const LAYER_CFG = [
  { labelKey: 'ontology.lcfg0', color: '#34D399' },
  { labelKey: 'ontology.lcfg1', color: '#FB923C' },
  { labelKey: 'ontology.lcfg2', color: '#F87171' },
  { labelKey: 'ontology.lcfg3', color: '#818CF8' },
];

const TYPE_TO_LAYER = { signal: 0, event: 1, impact: 2, response: 3 };

/* --- layout: layer별 Y 좌표 자동 배치 --- */
function layoutNodes(rawNodes) {
  const buckets = [[], [], [], []];
  for (const n of rawNodes) {
    const layer = n.layer ?? TYPE_TO_LAYER[n.type] ?? 0;
    buckets[layer].push({ ...n, layer });
  }
  const positioned = [];
  for (let l = 0; l < 4; l++) {
    const lx = PAD_X + l * COL_GAP;
    buckets[l].forEach((n, i) => {
      positioned.push({ ...n, x: lx, y: PAD_Y + i * ROW_GAP });
    });
  }
  return positioned;
}

function epath(fn, tn) {
  const x1 = fn.x + NW;
  const y1 = fn.y + NH / 2;
  const x2 = tn.x;
  const y2 = tn.y + NH / 2;
  const c  = (x2 - x1) * 0.45;
  return `M ${x1} ${y1} C ${x1 + c} ${y1}, ${x2 - c} ${y2}, ${x2} ${y2}`;
}

/* --- 하드코딩 fallback (data 없을 때) --- */
const FALLBACK_NODES = [
  { id: 's1', layer: 0, label: 'Signal 1' },
  { id: 's2', layer: 0, label: 'Signal 2' },
  { id: 'e1', layer: 1, label: 'Event 1' },
  { id: 'e2', layer: 1, label: 'Event 2' },
  { id: 'i1', layer: 2, label: 'Impact 1' },
  { id: 'i2', layer: 2, label: 'Impact 2' },
  { id: 'r1', layer: 3, label: 'Response 1' },
  { id: 'r2', layer: 3, label: 'Response 2' },
];
const FALLBACK_LINKS = [
  { source: 's1', target: 'e1' }, { source: 's2', target: 'e2' },
  { source: 'e1', target: 'i1' }, { source: 'e2', target: 'i2' },
  { source: 'i1', target: 'r1' }, { source: 'i2', target: 'r2' },
];

function DynamicDAG({ nodes: rawNodes, links: rawLinks }) {
  const { t } = useLang();

  const { nodes, nodeMap, edges, svgW, svgH } = useMemo(() => {
    const laid = layoutNodes(rawNodes);
    const nm = Object.fromEntries(laid.map((n) => [n.id, n]));
    const maxY = Math.max(...laid.map((n) => n.y), 0);
    return {
      nodes: laid,
      nodeMap: nm,
      edges: rawLinks.filter((l) => nm[l.source] && nm[l.target]),
      svgW: PAD_X + 3 * COL_GAP + NW + PAD_X,
      svgH: maxY + NH + 20,
    };
  }, [rawNodes, rawLinks]);

  return (
    <svg viewBox={`0 0 ${svgW} ${svgH}`} width="100%" style={{ minWidth: 480 }}>
      <defs>
        <marker id="dag-a" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
          <path d="M0,0 L0,6 L8,3 z" fill="#475569" />
        </marker>
        <marker id="dag-ar" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
          <path d="M0,0 L0,6 L8,3 z" fill="#F87171" />
        </marker>
      </defs>

      {/* layer headers */}
      {LAYER_CFG.map((cfg, i) => {
        const lx = PAD_X + i * COL_GAP;
        return (
          <g key={i}>
            <rect x={lx} y={0} width={NW} height={22} rx={5}
              fill={cfg.color} fillOpacity={0.12}
              stroke={cfg.color} strokeWidth={1} strokeOpacity={0.35} />
            <text x={lx + NW / 2} y={14}
              textAnchor="middle" fontSize={10} fontWeight="700" fill={cfg.color}>
              {t(cfg.labelKey)}
            </text>
          </g>
        );
      })}

      {/* edges */}
      {edges.map((e, i) => {
        const fn = nodeMap[e.source];
        const tn = nodeMap[e.target];
        const isHigh = (fn.severity || 0) >= 7 || (tn.severity || 0) >= 7;
        return (
          <path key={i} d={epath(fn, tn)} fill="none"
            stroke={isHigh ? '#F87171' : '#334155'}
            strokeWidth={isHigh ? 2 : 1}
            strokeOpacity={isHigh ? 0.9 : 0.55}
            markerEnd={isHigh ? 'url(#dag-ar)' : 'url(#dag-a)'} />
        );
      })}

      {/* nodes */}
      {nodes.map((n) => {
        const cfg = LAYER_CFG[n.layer] || LAYER_CFG[0];
        const label = n.label || n.id;
        const truncated = label.length > 16 ? label.slice(0, 15) + '…' : label;
        return (
          <g key={n.id}>
            <rect x={n.x} y={n.y} width={NW} height={NH} rx={6}
              fill="#0f172a"
              stroke={cfg.color} strokeWidth={1.5} strokeOpacity={0.65} />
            <text x={n.x + NW / 2} y={n.y + NH / 2}
              textAnchor="middle" dominantBaseline="central"
              fontSize={10} fontWeight="500" fill="#cbd5e1">
              {truncated}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export default function OntologyGraph({ data, loading, error }) {
  const { t } = useLang();

  const hasData = data?.nodes?.length > 0;
  const nodes = hasData ? data.nodes : FALLBACK_NODES;
  const links = hasData ? data.links : FALLBACK_LINKS;

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

      <DynamicDAG nodes={nodes} links={links} />

      {/* legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-3 px-1">
        {LAYER_CFG.map((cfg, i) => (
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
