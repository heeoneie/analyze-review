import { AlertTriangle, ShoppingCart, Youtube, PenSquare, MessageSquare, TrendingUp } from 'lucide-react';

const PLATFORM_CONFIG = {
  'Coupang': {
    icon: ShoppingCart,
    label: '이커머스 리뷰',
    type: '내부 채널',
  },
  'YouTube': {
    icon: Youtube,
    label: '영상 댓글',
    type: '외부 채널',
  },
  'Naver Blog': {
    icon: PenSquare,
    label: '블로그 포스트',
    type: '외부 채널',
  },
  'Community (뽐뿌)': {
    icon: MessageSquare,
    label: '커뮤니티 게시글',
    type: '외부 채널',
  },
};

const VIRAL_RISK_CFG = {
  '높음': { cls: 'bg-red-950 text-red-400 border border-red-800', dot: 'bg-red-500', pulse: true },
  '보통': { cls: 'bg-amber-950 text-amber-400 border border-amber-800', dot: 'bg-amber-400', pulse: false },
  '낮음': { cls: 'bg-slate-800 text-slate-400 border border-slate-700', dot: 'bg-slate-500', pulse: false },
};

function ViralRiskBadge({ risk }) {
  const cfg = VIRAL_RISK_CFG[risk] || VIRAL_RISK_CFG['낮음'];
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold ${cfg.cls}`}>
      <span className="relative flex h-1.5 w-1.5">
        {cfg.pulse && (
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${cfg.dot} opacity-60`} />
        )}
        <span className={`relative inline-flex rounded-full h-1.5 w-1.5 ${cfg.dot}`} />
      </span>
      역바이럴 {risk}
    </span>
  );
}

function CommentGrowthChart({ growth, metricLabel }) {
  if (!growth?.length) return null;

  const max = Math.max(...growth.map((p) => p.delta));
  const MAX_H = 28;

  const first = growth[0].delta;
  const last = growth[growth.length - 1].delta;
  const ratio = last / (first || 1);
  const trend =
    ratio >= 3
      ? { label: '↑ 급증', cls: 'text-red-400 font-bold' }
      : ratio >= 1.8
      ? { label: '↑ 증가', cls: 'text-amber-400 font-semibold' }
      : { label: '→ 완만', cls: 'text-slate-500' };

  return (
    <div className="mt-2.5 pt-2.5 border-t border-slate-700">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] font-medium text-slate-500 flex items-center gap-1">
          <TrendingUp size={11} />
          {metricLabel || '반응'} 추이 (5분 간격)
        </span>
        <span className={`text-[11px] ${trend.cls}`}>{trend.label}</span>
      </div>
      <div className="flex items-end gap-3">
        {growth.map((point, i) => {
          const barH = Math.max(4, Math.round((point.delta / max) * MAX_H));
          const isLast = i === growth.length - 1;
          return (
            <div key={i} className="flex flex-col items-center gap-0.5">
              <span className={`text-[11px] font-bold ${isLast ? 'text-red-400' : 'text-slate-400'}`}>
                +{point.delta.toLocaleString()}
              </span>
              <div
                className={`w-5 rounded-t ${isLast ? 'bg-red-600' : 'bg-slate-600'}`}
                style={{ height: `${barH}px` }}
              />
              <span className="text-[10px] text-slate-600 mt-0.5">{point.t}</span>
            </div>
          );
        })}
        <span className="text-[10px] text-slate-600 self-end pb-4 ml-0.5">({metricLabel})</span>
      </div>
    </div>
  );
}

export default function MockScenario({ data }) {
  if (!data) return null;

  const { risk_level, incident_title, incident_summary, clustering_reason, channel_signals } = data;

  const alertBorder =
    risk_level === 'RED' ? 'border-red-800 bg-red-950/40' :
    risk_level === 'ORANGE' ? 'border-orange-800 bg-orange-950/40' :
    'border-amber-800 bg-amber-950/40';

  return (
    <div className="space-y-4">
      {/* Red Alert Banner */}
      <div className={`rounded-2xl border ${alertBorder} p-5`}>
        <div className="flex items-start gap-3">
          <AlertTriangle
            className={`mt-0.5 flex-shrink-0 ${risk_level === 'RED' ? 'text-red-400' : 'text-amber-400'}`}
            size={20}
          />
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <h3 className="font-bold text-white">{incident_title}</h3>
              <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold ${
                risk_level === 'RED' ? 'bg-red-900 text-red-300' : 'bg-amber-900 text-amber-300'
              }`}>
                {risk_level === 'RED' && (
                  <span className="relative flex h-1.5 w-1.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-60" />
                    <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-red-400" />
                  </span>
                )}
                {risk_level === 'RED' ? '치명적' : risk_level === 'ORANGE' ? '경고' : '주의'}
              </span>
            </div>
            <p className="text-sm text-slate-300 leading-relaxed">{incident_summary}</p>
            {clustering_reason && (
              <p className="text-xs text-slate-500 mt-2 bg-slate-900/60 rounded-lg px-3 py-1.5 border border-slate-800">
                🔗 {clustering_reason}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Channel Signals */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <span className="text-sm font-semibold text-slate-200">감지된 채널 신호</span>
          <span className="px-2 py-0.5 bg-slate-800 text-slate-400 text-xs rounded-full border border-slate-700">
            {channel_signals?.length}개 채널
          </span>
          <span className="text-xs text-slate-600 ml-auto">내부 + 외부 여론 채널</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {channel_signals?.map((signal, idx) => {
            const cfg = PLATFORM_CONFIG[signal.platform] || {
              icon: MessageSquare,
              label: signal.data_type,
              type: '채널',
            };
            const Icon = cfg.icon;
            return (
              <div key={idx} className="border border-slate-700 bg-slate-900 rounded-xl p-4">
                {/* Header */}
                <div className="flex items-center justify-between mb-2.5">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 bg-slate-800 rounded-lg flex items-center justify-center">
                      <Icon size={14} className="text-slate-400" />
                    </div>
                    <span className="text-sm font-semibold text-slate-200">{signal.platform}</span>
                  </div>
                  <div className="flex items-center gap-1.5 flex-wrap justify-end">
                    {signal.viral_risk && <ViralRiskBadge risk={signal.viral_risk} />}
                    <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                      {cfg.type}
                    </span>
                    <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                      {cfg.label}
                    </span>
                  </div>
                </div>

                {/* Content */}
                <p className="text-xs text-slate-400 leading-relaxed line-clamp-3 mb-2.5">
                  &ldquo;{signal.content}&rdquo;
                </p>

                {/* Risk Indicators */}
                <div className="flex flex-wrap gap-1">
                  {signal.risk_indicators?.map((ind, i) => (
                    <span
                      key={i}
                      className="text-xs px-2 py-0.5 bg-red-950 text-red-400 border border-red-800 rounded-full font-medium"
                    >
                      △ {ind}
                    </span>
                  ))}
                </div>

                {/* Metadata */}
                {signal.metadata && (
                  <p className="text-[11px] text-slate-600 mt-2">
                    {signal.metadata.rating && `★ ${signal.metadata.rating}/5 · `}
                    {signal.metadata.likes && `좋아요 ${signal.metadata.likes} · `}
                    {signal.metadata.visitor_count && `조회 ${signal.metadata.visitor_count.toLocaleString()} · `}
                    {signal.metadata.view_count && `뷰 ${signal.metadata.view_count.toLocaleString()} · `}
                    {new Date(signal.metadata.timestamp).toLocaleDateString('ko-KR')}
                  </p>
                )}

                {/* Comment Growth */}
                <CommentGrowthChart
                  growth={signal.comment_growth}
                  metricLabel={signal.metric_label}
                />
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
