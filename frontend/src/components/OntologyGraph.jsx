import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
} from '@xyflow/react';
import dagre from '@dagrejs/dagre';
import {
  Network,
  Loader2,
  AlertTriangle,
  Radio,
  Shield,
  Building2,
  Zap,
  X,
  SlidersHorizontal,
} from 'lucide-react';
import { useLang } from '../contexts/LangContext';

/* ────────────────────────────────────────────
   Dagre layout — defined OUTSIDE component
   to prevent recreation on every render
   ──────────────────────────────────────────── */
const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const NODE_WIDTH = 250;
const NODE_HEIGHT = 80;

function getLayoutedElements(nodes, edges) {
  dagreGraph.setGraph({ rankdir: 'LR' });

  // Clear stale data from previous layout runs
  dagreGraph.nodes().forEach((n) => {
    dagreGraph.removeNode(n);
  });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const pos = dagreGraph.node(node.id);
    const fallback = node.position ?? { x: 0, y: 0 };
    return {
      ...node,
      position: {
        x: (pos?.x ?? fallback.x) - NODE_WIDTH / 2,
        y: (pos?.y ?? fallback.y) - NODE_HEIGHT / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
}

/* ────────────────────────────────────────────
   Custom Node — defined OUTSIDE component
   ──────────────────────────────────────────── */
const TYPE_ICONS = {
  signal: Radio,
  event: AlertTriangle,
  impact: Zap,
  response: Shield,
  category: AlertTriangle,
  root_cause: Zap,
  department: Building2,
  risk_type: Shield,
};

function CustomRiskNode({ data }) {
  const severity = data.severity_score ?? 0;
  const Icon = TYPE_ICONS[data.type] || Network;

  let borderColor, shadowClass, badgeColor;
  if (severity >= 8) {
    borderColor = 'border-rose-500';
    shadowClass = 'shadow-[0_0_15px_rgba(225,29,72,0.3)]';
    badgeColor = 'bg-rose-500/20 text-rose-400';
  } else if (severity >= 5) {
    borderColor = 'border-amber-500';
    shadowClass = 'shadow-[0_0_10px_rgba(245,158,11,0.2)]';
    badgeColor = 'bg-amber-500/20 text-amber-400';
  } else {
    borderColor = 'border-emerald-600';
    shadowClass = '';
    badgeColor = 'bg-emerald-500/20 text-emerald-400';
  }

  return (
    <div
      className={`bg-zinc-900 ${borderColor} border text-zinc-100 ${shadowClass} rounded-lg p-3 min-w-[200px]`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!bg-zinc-600 !w-2 !h-2 !border-0"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!bg-zinc-600 !w-2 !h-2 !border-0"
      />

      <div className="flex items-center gap-2 mb-1">
        <Icon size={14} className="text-zinc-400 flex-shrink-0" />
        <span className="text-xs text-zinc-500 capitalize">{data.type}</span>
        <span
          className={`text-[10px] px-1.5 py-0.5 rounded-full ml-auto font-medium ${badgeColor}`}
        >
          {severity.toFixed(1)}
        </span>
      </div>

      <div
        className="text-sm font-medium text-zinc-100 leading-tight truncate"
        title={data.label}
      >
        {data.label}
      </div>
    </div>
  );
}

const nodeTypes = { custom: CustomRiskNode };

/* ────────────────────────────────────────────
   Severity helpers
   ──────────────────────────────────────────── */
function severityBorder(score) {
  if (score >= 8) return 'border-rose-500';
  if (score >= 5) return 'border-amber-500';
  return 'border-emerald-600';
}

function severityBadge(score) {
  if (score >= 8) return 'bg-rose-500/20 text-rose-400';
  if (score >= 5) return 'bg-amber-500/20 text-amber-400';
  return 'bg-emerald-500/20 text-emerald-400';
}

function severityLabel(score) {
  if (score >= 8) return 'Critical';
  if (score >= 5) return 'Warning';
  return 'Safe';
}

/* ────────────────────────────────────────────
   Main Component
   ──────────────────────────────────────────── */
export default function OntologyGraph({ data, loading, error: parentError }) {
  const { t } = useLang();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [fetchError, setFetchError] = useState(null);

  // WOW 1: Severity filter
  const [minSeverity, setMinSeverity] = useState(0);

  // WOW 2: Node click side panel
  const [selectedNode, setSelectedNode] = useState(null);

  // Track whether first fetch has completed (for debounce skip)
  const hasMounted = useRef(false);

  /* --- Apply nodes + edges through dagre layout --- */
  const applyGraphData = useCallback((rawNodes, rawEdges) => {
    const processedNodes = rawNodes.map((n) => ({
      ...n,
      id: String(n.id),
      type: 'custom',
      data: {
        label: n.data?.label ?? n.label ?? n.id,
        type: n.data?.type ?? n.type ?? 'signal',
        severity_score: n.data?.severity_score ?? n.severity ?? 0,
      },
      position: n.position ?? { x: 0, y: 0 },
    }));

    const nodeMap = new Map(processedNodes.map((n) => [n.id, n]));

    const processedEdges = rawEdges.map((e, i) => {
      const sourceNode = nodeMap.get(String(e.source));
      const targetNode = nodeMap.get(String(e.target));
      const maxSeverity = Math.max(
        sourceNode?.data?.severity_score ?? 0,
        targetNode?.data?.severity_score ?? 0,
      );
      const isCritical = maxSeverity >= 8;

      return {
        id: String(e.id ?? `e-${e.source}-${e.target}-${i}`),
        source: String(e.source),
        target: String(e.target),
        label: e.label ?? e.relation ?? '',
        type: 'default',
        style: isCritical
          ? { stroke: '#e11d48', strokeWidth: 3, filter: 'drop-shadow(0 0 5px #e11d48)' }
          : { stroke: '#52525b', strokeWidth: 1 },
        animated: isCritical,
        labelStyle: { fill: '#a1a1aa', fontSize: 11 },
        data: e.data ?? {},
      };
    });

    const { nodes: laid, edges: laidEdges } = getLayoutedElements(
      processedNodes,
      processedEdges,
    );
    setNodes(laid);
    setEdges(laidEdges);
  }, [setNodes, setEdges]);

  /* --- Single unified useEffect: props.data override OR API fetch --- */
  useEffect(() => {
    // If parent provides live-generated data, use it — skip fetch
    if (data?.nodes?.length) {
      const rfNodes = data.nodes.map((n) => ({
        id: String(n.id),
        type: 'custom',
        data: {
          label: n.data?.label ?? n.label ?? n.id,
          type: n.data?.type ?? n.type ?? 'signal',
          severity_score: n.data?.severity_score ?? n.severity ?? 0,
        },
        position: n.position ?? { x: 0, y: 0 },
      }));

      const rfEdges = (data.edges ?? data.links ?? []).map((e, i) => ({
        id: String(e.id ?? `e-${e.source}-${e.target}-${i}`),
        source: String(e.source),
        target: String(e.target),
        label: e.label ?? e.relation ?? '',
        data: e.data ?? {},
      }));

      applyGraphData(rfNodes, rfEdges);
      return;
    }

    // Fetch persisted graph — debounce slider changes, immediate on mount
    const controller = new AbortController();
    const delay = hasMounted.current ? 200 : 0;
    hasMounted.current = true;

    const timer = setTimeout(() => {
      const baseURL =
        import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
      setIsLoading(true);
      setFetchError(null);

      fetch(
        `${baseURL}/risk/ontology/graph?limit=100&min_severity=${minSeverity}`,
        { signal: controller.signal },
      )
        .then((res) => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          return res.json();
        })
        .then((result) => {
          if (result.nodes?.length > 0) {
            applyGraphData(result.nodes, result.edges ?? []);
          } else {
            setNodes([]);
            setEdges([]);
          }
        })
        .catch((err) => {
          if (err.name !== 'AbortError') {
            setFetchError(err.message);
          }
        })
        .finally(() => {
          setIsLoading(false);
        });
    }, delay);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [minSeverity, data, applyGraphData, setNodes, setEdges]);

  /* --- Node click handler --- */
  const onNodeClick = useCallback((_event, node) => {
    setSelectedNode(node);
  }, []);

  const displayError = parentError || fetchError;
  const showLoading = loading || isLoading;
  const isLiveOverride = Boolean(data?.nodes?.length);

  return (
    <div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-6">
      {/* Header */}
      <div className="flex items-center gap-2 mb-5">
        <Network className="text-zinc-400" size={18} />
        <h3 className="text-base font-bold text-white">
          {t('ontology.title')}
        </h3>
        {showLoading && (
          <span className="flex items-center gap-1 text-xs text-zinc-500 ml-1">
            <Loader2 className="animate-spin" size={12} />
            {t('ontology.analyzing')}
          </span>
        )}
      </div>

      {/* Error banner */}
      {displayError && (
        <div className="bg-red-950 text-red-400 border border-red-800 rounded-lg px-4 py-2 text-sm mb-4">
          {displayError}
        </div>
      )}

      {/* Graph container — relative for absolute overlays */}
      <div className="relative h-[600px] w-full border border-zinc-800 rounded-xl overflow-hidden bg-zinc-950">
        {showLoading && nodes.length === 0 ? (
          <div className="flex items-center justify-center h-full text-zinc-500">
            <Loader2 className="animate-spin mr-2" size={20} />
            <span className="text-sm">Loading graph…</span>
          </div>
        ) : nodes.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-zinc-500 gap-3">
            <Network size={32} className="text-zinc-600" />
            <p className="text-sm">No graph data available</p>
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes}
            fitView
            minZoom={0.2}
            maxZoom={2}
            defaultEdgeOptions={{ type: 'default' }}
          >
            <Background color="#27272a" gap={20} />
            <Controls
              className="!bg-zinc-800 !border-zinc-700 !rounded-lg
                [&>button]:!bg-zinc-800 [&>button]:!border-zinc-700
                [&>button]:!text-zinc-400 [&>button:hover]:!bg-zinc-700"
            />
            <MiniMap
              nodeColor={(n) =>
                n.data?.severity_score >= 8
                  ? '#e11d48'
                  : n.data?.severity_score >= 5
                    ? '#d97706'
                    : '#10b981'
              }
              maskColor="rgba(0,0,0,0.7)"
              className="!bg-zinc-900 !border-zinc-700"
            />
          </ReactFlow>
        )}

        {/* ── WOW 1: Severity Filter Slider ── */}
        <div className="absolute bottom-3 left-3 z-10 flex items-center gap-2.5
          bg-zinc-900/80 backdrop-blur-md border border-zinc-700/60 rounded-lg px-3 py-2"
        >
          <SlidersHorizontal size={13} className={`flex-shrink-0 ${isLiveOverride ? 'text-zinc-600' : 'text-zinc-500'}`} />
          <input
            type="range"
            aria-label="Minimum severity filter"
            min={0}
            max={10}
            step={0.5}
            value={minSeverity}
            disabled={isLiveOverride}
            onChange={(e) => setMinSeverity(Number(e.target.value))}
            className={`w-28 h-1 appearance-none rounded-full
              [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3
              [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full
              [&::-webkit-slider-thumb]:shadow-sm
              ${isLiveOverride
                ? 'bg-zinc-800 cursor-not-allowed [&::-webkit-slider-thumb]:bg-zinc-600'
                : 'bg-zinc-700 cursor-pointer [&::-webkit-slider-thumb]:bg-zinc-300 [&::-webkit-slider-thumb]:cursor-pointer'
              }`}
          />
          {isLiveOverride ? (
            <span className="text-[10px] text-amber-400/80 font-medium whitespace-nowrap">
              Live Override
            </span>
          ) : (
            <span className="text-[11px] text-zinc-400 font-mono w-8 text-right tabular-nums">
              ≥{minSeverity.toFixed(1)}
            </span>
          )}
        </div>

        {/* ── WOW 2: Node Click Side Panel ── */}
        {selectedNode && (
          <div className="absolute inset-0 z-20 pointer-events-none">
          <div
            className="absolute top-0 right-0 h-full w-72 pointer-events-auto
              bg-zinc-900/85 backdrop-blur-xl border-l border-zinc-700/60
              flex flex-col overflow-hidden"
          >
            {/* Panel header */}
            <div className="flex items-center justify-between px-4 pt-4 pb-3 border-b border-zinc-800">
              <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                Node Detail
              </span>
              <button
                type="button"
                aria-label="Close node detail"
                onClick={() => setSelectedNode(null)}
                className="p-1 rounded-md text-zinc-500 hover:text-zinc-300
                  hover:bg-zinc-800 transition-colors"
              >
                <X size={14} />
              </button>
            </div>

            {/* Panel body */}
            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
              {/* Label + type */}
              <div>
                <h4 className="text-sm font-bold text-zinc-100 leading-snug mb-1">
                  {selectedNode.data.label}
                </h4>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] text-zinc-500 capitalize bg-zinc-800 rounded px-1.5 py-0.5">
                    {selectedNode.data.type}
                  </span>
                </div>
              </div>

              {/* Severity score card */}
              <div
                className={`rounded-lg border p-3 ${severityBorder(selectedNode.data.severity_score ?? 0)}`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[11px] text-zinc-500 font-medium uppercase tracking-wide">
                    Severity Score
                  </span>
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${severityBadge(selectedNode.data.severity_score ?? 0)}`}
                  >
                    {severityLabel(selectedNode.data.severity_score ?? 0)}
                  </span>
                </div>
                <p className="text-2xl font-bold text-zinc-100 tabular-nums">
                  {(selectedNode.data.severity_score ?? 0).toFixed(1)}
                  <span className="text-xs text-zinc-500 font-normal ml-1">/ 10</span>
                </p>
              </div>

              {/* Evidence placeholder */}
              <div>
                <h5 className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider mb-2">
                  Associated Risk Signals (Evidence)
                </h5>
                <div className="space-y-2">
                  {[1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className="h-10 rounded-md bg-zinc-800/60 border border-zinc-700/40
                        animate-pulse"
                    />
                  ))}
                </div>
                <p className="text-[10px] text-zinc-600 mt-2 text-center">
                  Evidence linking coming soon
                </p>
              </div>
            </div>
          </div>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-3 px-1">
        {[
          { color: '#e11d48', label: 'Critical (≥8)' },
          { color: '#d97706', label: 'Warning (5–7)' },
          { color: '#10b981', label: 'Safe (<5)' },
        ].map((item) => (
          <div
            key={item.label}
            className="flex items-center gap-1.5 text-xs text-zinc-500"
          >
            <span
              className="w-2 h-2 rounded-sm flex-shrink-0"
              style={{ backgroundColor: item.color }}
            />
            {item.label}
          </div>
        ))}
        <div className="flex items-center gap-1.5 text-xs text-zinc-500 ml-2 border-l border-zinc-700 pl-3">
          <span
            className="inline-block w-5 h-0.5 flex-shrink-0"
            style={{ background: '#e11d48' }}
          />
          {t('ontology.escalation')}
        </div>
      </div>

      {/* Summary text */}
      {data?.summary && (
        <p className="mt-3 text-sm text-zinc-400 bg-zinc-800 border border-zinc-700 rounded-lg p-3 leading-relaxed">
          {data.summary}
        </p>
      )}
    </div>
  );
}
