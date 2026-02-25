import { useEffect, useState } from 'react';
import { getDatasetInfo, getEvaluationMetrics } from '../api/client';

const CATEGORY_LABELS = {
  delivery_delay: 'Delivery Delay',
  wrong_item: 'Wrong Item',
  poor_quality: 'Poor Quality',
  damaged_packaging: 'Damaged Packaging',
  size_issue: 'Size Issue',
  missing_parts: 'Missing Parts',
  not_as_described: 'Not As Described',
  customer_service: 'Customer Service',
  price_issue: 'Price Issue',
  other: 'Other',
};

function MetricBar({ value = 0, color = 'bg-emerald-500' }) {
  const safe = Math.min(Math.max(Number(value) || 0, 0), 1);
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
        <div
          className={`h-full ${color} rounded-full transition-all duration-700`}
          style={{ width: `${(safe * 100).toFixed(1)}%` }}
        />
      </div>
      <span className="text-xs text-zinc-300 w-12 text-right font-mono">
        {(safe * 100).toFixed(1)}%
      </span>
    </div>
  );
}

function ScoreBadge({ value = 0 }) {
  const safe = Math.min(Math.max(Number(value) || 0, 0), 1);
  const pct = safe * 100;
  const color =
    pct >= 85 ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10' :
    pct >= 75 ? 'text-yellow-400 border-yellow-500/30 bg-yellow-500/10' :
                'text-red-400 border-red-500/30 bg-red-500/10';
  return (
    <span className={`px-2 py-0.5 rounded border text-xs font-bold ${color}`}>
      {pct.toFixed(1)}%
    </span>
  );
}

export default function ModelQuality() {
  const [metrics, setMetrics] = useState(null);
  const [datasetInfo, setDatasetInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    Promise.all([
      getEvaluationMetrics().then((r) => r.data),
      getDatasetInfo().then((r) => r.data),
    ])
      .then(([m, d]) => {
        setMetrics(m);
        setDatasetInfo(d);
      })
      .catch((err) => {
        console.error('ModelQuality fetch failed:', err);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="border border-zinc-800 rounded-xl p-4 animate-pulse">
        <div className="h-4 bg-zinc-800 rounded w-48 mb-2" />
        <div className="h-3 bg-zinc-800 rounded w-32" />
      </div>
    );
  }

  if (!metrics) return null;

  const { overall, per_class, meta, rag_comparison, error_analysis } = metrics;
  if (!overall) return null;

  const topCategories = Object.entries(per_class || {})
    .sort((a, b) => b[1].f1 - a[1].f1)
    .slice(0, 5);

  return (
    <div className="border border-zinc-800 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3 bg-zinc-900/60 border-b border-zinc-800 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-1.5 h-4 bg-violet-500 rounded-full" />
          <span className="text-sm font-semibold text-zinc-100">AI Model Quality</span>
          <span className="px-2 py-0.5 text-xs bg-zinc-800 text-zinc-400 rounded border border-zinc-700">
            {meta?.model || 'gpt-4o-mini'}
          </span>
        </div>
        <div className="flex items-center gap-3">
          {datasetInfo && (
            <span className="text-xs text-zinc-500">
              n={datasetInfo.total_samples} · {Object.keys(datasetInfo.label_distribution || {}).length} classes
            </span>
          )}
          <button
            onClick={() => setExpanded((v) => !v)}
            className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            {expanded ? '접기' : '상세 보기'}
          </button>
        </div>
      </div>

      <div className="p-5 space-y-5">
        {/* Overall scores */}
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: 'Accuracy', value: overall.accuracy },
            { label: 'Precision', value: overall.precision_weighted },
            { label: 'Recall', value: overall.recall_weighted },
            { label: 'F1 Score', value: overall.f1_weighted },
          ].map(({ label, value }) => (
            <div key={label} className="bg-zinc-900 border border-zinc-800 rounded-lg p-3 text-center">
              <div className="text-lg font-bold text-white font-mono">
                {((Number(value) || 0) * 100).toFixed(1)}%
              </div>
              <div className="text-xs text-zinc-500 mt-0.5">{label}</div>
            </div>
          ))}
        </div>

        {/* RAG comparison */}
        {rag_comparison?.available && (
          <div className="bg-violet-500/5 border border-violet-500/20 rounded-lg p-3 flex items-center justify-between">
            <div className="text-xs text-zinc-400">
              <span className="text-violet-400 font-semibold">RAG-enhanced</span> vs Baseline
              <span className="ml-2 text-zinc-500">({rag_comparison.rag_model})</span>
            </div>
            <div className="flex items-center gap-4 text-xs font-mono">
              <span className="text-zinc-500">Baseline F1: {(rag_comparison.baseline_f1 * 100).toFixed(1)}%</span>
              <span className="text-violet-400 font-bold">
                RAG F1: {(rag_comparison.rag_f1 * 100).toFixed(1)}%
              </span>
              <span className="text-emerald-400 font-bold">{rag_comparison.improvement}</span>
            </div>
          </div>
        )}

        {/* Per-class breakdown (expandable) */}
        {expanded && (
          <div>
            <div className="text-xs text-zinc-500 mb-3 font-medium uppercase tracking-wider">
              Per-class F1 (top 5)
            </div>
            <div className="space-y-2.5">
              {topCategories.map(([key, cls]) => (
                <div key={key} className="grid grid-cols-[140px_1fr_auto] items-center gap-3">
                  <span className="text-xs text-zinc-400 truncate">
                    {CATEGORY_LABELS[key] || key}
                  </span>
                  <MetricBar value={cls.f1} />
                  <ScoreBadge value={cls.f1} />
                </div>
              ))}
            </div>

            {/* Error analysis */}
            {error_analysis && (
              <div className="mt-4 pt-4 border-t border-zinc-800">
                <div className="text-xs text-zinc-500 mb-2 font-medium uppercase tracking-wider">
                  Confusion (top misclassifications)
                </div>
                <div className="space-y-1.5">
                  {(error_analysis.most_confused_pairs || []).slice(0, 3).map((pair, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs text-zinc-500">
                      <span className="text-red-400">{CATEGORY_LABELS[pair.true] || pair.true}</span>
                      <span className="text-zinc-700">→</span>
                      <span className="text-yellow-400">{CATEGORY_LABELS[pair.predicted] || pair.predicted}</span>
                      <span className="ml-auto text-zinc-600">×{pair.count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="mt-3 text-xs text-zinc-600">
              Evaluated {meta?.evaluated_at ? new Date(meta.evaluated_at).toLocaleDateString('ko-KR') : ''} ·
              temp={meta?.temperature}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
