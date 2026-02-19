import { useRef, useCallback, useEffect, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Network, Loader2 } from 'lucide-react';

const NODE_COLORS = {
  category: '#EF4444',
  root_cause: '#F97316',
  department: '#3B82F6',
  risk_type: '#8B5CF6',
};

const NODE_LABELS = {
  category: '이슈 카테고리',
  root_cause: '근본 원인',
  department: '담당 부서',
  risk_type: '리스크 유형',
};

export default function OntologyGraph({ data, loading, error, onGenerate }) {
  const graphRef = useRef();
  const containerRef = useRef();
  const [dimensions, setDimensions] = useState({ width: 800, height: 450 });

  useEffect(() => {
    if (!containerRef.current) return;
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setDimensions({ width: entry.contentRect.width, height: 450 });
      }
    });
    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  useEffect(() => {
    if (data && graphRef.current) {
      setTimeout(() => graphRef.current?.zoomToFit(400, 40), 500);
    }
  }, [data]);

  const paintNode = useCallback((node, ctx) => {
    const size = 4 + (node.severity || 5) * 0.8;
    const color = NODE_COLORS[node.type] || '#6B7280';

    ctx.beginPath();
    ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    ctx.font = '3.5px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillStyle = '#374151';
    ctx.fillText(node.label || node.id, node.x, node.y + size + 2);
  }, []);

  const paintLink = useCallback((link, ctx) => {
    ctx.strokeStyle = '#D1D5DB';
    ctx.lineWidth = 0.8;
    ctx.beginPath();
    ctx.moveTo(link.source.x, link.source.y);
    ctx.lineTo(link.target.x, link.target.y);
    ctx.stroke();

    if (link.relation) {
      const midX = (link.source.x + link.target.x) / 2;
      const midY = (link.source.y + link.target.y) / 2;
      ctx.font = '2.5px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillStyle = '#9CA3AF';
      ctx.fillText(link.relation, midX, midY - 2);
    }
  }, []);

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
        <div className="flex items-center justify-center h-[450px] text-gray-400">
          <Loader2 className="animate-spin mr-2" size={20} />
          온톨로지 그래프 생성 중...
        </div>
      ) : data ? (
        <>
          {/* Legend */}
          <div className="flex flex-wrap gap-4 mb-3">
            {Object.entries(NODE_LABELS).map(([type, label]) => (
              <div key={type} className="flex items-center gap-1.5 text-xs text-gray-600">
                <span
                  className="w-3 h-3 rounded-full inline-block"
                  style={{ backgroundColor: NODE_COLORS[type] }}
                />
                {label}
              </div>
            ))}
          </div>

          {/* Graph */}
          <div
            ref={containerRef}
            className="border border-gray-100 rounded-xl overflow-hidden bg-gray-50"
          >
            <ForceGraph2D
              ref={graphRef}
              graphData={{ nodes: data.nodes || [], links: data.links || [] }}
              width={dimensions.width}
              height={dimensions.height}
              nodeCanvasObject={paintNode}
              linkCanvasObject={paintLink}
              nodePointerAreaPaint={(node, color, ctx) => {
                const size = 4 + (node.severity || 5) * 0.8;
                ctx.beginPath();
                ctx.arc(node.x, node.y, size + 2, 0, 2 * Math.PI);
                ctx.fillStyle = color;
                ctx.fill();
              }}
              cooldownTicks={100}
              d3AlphaDecay={0.02}
              d3VelocityDecay={0.3}
            />
          </div>

          {/* Summary */}
          {data.summary && (
            <p className="mt-3 text-sm text-gray-600 bg-purple-50 rounded-lg p-3">
              {data.summary}
            </p>
          )}
        </>
      ) : (
        <div className="flex items-center justify-center h-[450px] text-gray-300 text-sm">
          &quot;전체 리스크 분석 실행&quot; 또는 &quot;온톨로지 생성&quot; 버튼을 클릭하세요
        </div>
      )}
    </div>
  );
}
