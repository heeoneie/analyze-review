import { AlertTriangle, ShoppingCart, Youtube, PenSquare, MessageSquare, TrendingUp } from 'lucide-react';

const PLATFORM_CONFIG = {
  'Coupang': {
    icon: ShoppingCart,
    color: 'border-orange-300 bg-orange-50',
    badge: 'bg-orange-100 text-orange-700',
    label: '이커머스 리뷰',
    type: '내부 채널',
    typeColor: 'bg-blue-100 text-blue-700',
  },
  'YouTube': {
    icon: Youtube,
    color: 'border-red-300 bg-red-50',
    badge: 'bg-red-100 text-red-700',
    label: '영상 댓글',
    type: '외부 채널',
    typeColor: 'bg-purple-100 text-purple-700',
  },
  'Naver Blog': {
    icon: PenSquare,
    color: 'border-green-300 bg-green-50',
    badge: 'bg-green-100 text-green-700',
    label: '블로그 포스트',
    type: '외부 채널',
    typeColor: 'bg-purple-100 text-purple-700',
  },
  'Community (뽐뿌)': {
    icon: MessageSquare,
    color: 'border-blue-300 bg-blue-50',
    badge: 'bg-blue-100 text-blue-700',
    label: '커뮤니티 게시글',
    type: '외부 채널',
    typeColor: 'bg-purple-100 text-purple-700',
  },
};

const RISK_LEVEL_STYLES = {
  GREEN: { bg: 'bg-green-500', text: '안전', pulse: false },
  YELLOW: { bg: 'bg-yellow-400', text: '주의', pulse: false },
  ORANGE: { bg: 'bg-orange-500', text: '경고', pulse: true },
  RED: { bg: 'bg-red-600', text: '치명적', pulse: true },
};

const VIRAL_RISK_CFG = {
  '높음': { bg: 'bg-red-100', text: 'text-red-700', dot: 'bg-red-500', pulse: true },
  '보통': { bg: 'bg-orange-100', text: 'text-orange-700', dot: 'bg-orange-400', pulse: false },
  '낮음': { bg: 'bg-gray-100', text: 'text-gray-500', dot: 'bg-gray-400', pulse: false },
};

function RiskBadge({ level }) {
  const style = RISK_LEVEL_STYLES[level] || RISK_LEVEL_STYLES.GREEN;
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-white text-sm font-bold ${style.bg}`}>
      {style.pulse && (
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-white" />
        </span>
      )}
      {style.text}
    </span>
  );
}

function ViralRiskBadge({ risk }) {
  const cfg = VIRAL_RISK_CFG[risk] || VIRAL_RISK_CFG['낮음'];
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold ${cfg.bg} ${cfg.text}`}>
      <span className={`relative flex h-1.5 w-1.5`}>
        {cfg.pulse && (
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${cfg.dot} opacity-75`} />
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
  const MAX_H = 28; // px

  const first = growth[0].delta;
  const last = growth[growth.length - 1].delta;
  const ratio = last / (first || 1);
  const trend =
    ratio >= 3
      ? { label: '↑ 급증', cls: 'text-red-600 font-bold' }
      : ratio >= 1.8
      ? { label: '↑ 증가', cls: 'text-orange-500 font-semibold' }
      : { label: '→ 완만', cls: 'text-gray-400' };

  return (
    <div className="mt-2.5 pt-2.5 border-t border-dashed border-gray-200">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-gray-500 flex items-center gap-1">
          <TrendingUp size={11} className="text-gray-400" />
          {metricLabel || '반응'} 증가 추이 (5분 간격)
        </span>
        <span className={`text-xs ${trend.cls}`}>{trend.label}</span>
      </div>
      <div className="flex items-end gap-3">
        {growth.map((point, i) => {
          const barH = Math.max(4, Math.round((point.delta / max) * MAX_H));
          const isLast = i === growth.length - 1;
          return (
            <div key={i} className="flex flex-col items-center gap-0.5">
              <span className={`text-[11px] font-bold ${isLast ? 'text-red-600' : 'text-orange-500'}`}>
                +{point.delta.toLocaleString()}
              </span>
              <div
                className={`w-5 rounded-t transition-all ${isLast ? 'bg-red-400' : 'bg-orange-300'}`}
                style={{ height: `${barH}px` }}
              />
              <span className="text-[10px] text-gray-400 mt-0.5">{point.t}</span>
            </div>
          );
        })}
        <span className="text-[10px] text-gray-400 self-end pb-4 ml-0.5">
          ({metricLabel})
        </span>
      </div>
    </div>
  );
}

export default function MockScenario({ data }) {
  if (!data) return null;

  const { risk_level, incident_title, incident_summary, clustering_reason, channel_signals } = data;

  return (
    <div className="space-y-4">
      {/* Red Alert Banner */}
      <div className={`rounded-2xl border-2 p-5 ${
        risk_level === 'RED'
          ? 'border-red-400 bg-red-50'
          : risk_level === 'ORANGE'
          ? 'border-orange-400 bg-orange-50'
          : 'border-yellow-400 bg-yellow-50'
      }`}>
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <AlertTriangle
              className={`mt-0.5 flex-shrink-0 ${risk_level === 'RED' ? 'text-red-500' : 'text-orange-500'}`}
              size={22}
            />
            <div>
              <div className="flex items-center gap-2 mb-1">
                <h3 className="font-bold text-gray-900">{incident_title}</h3>
                <RiskBadge level={risk_level} />
              </div>
              <p className="text-sm text-gray-700 leading-relaxed">{incident_summary}</p>
              {clustering_reason && (
                <p className="text-xs text-gray-500 mt-2 bg-white/60 rounded-lg px-3 py-1.5">
                  🔗 {clustering_reason}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Channel Signals — 2x2 Grid */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <span className="text-sm font-semibold text-gray-700">감지된 채널 신호</span>
          <span className="px-2 py-0.5 bg-gray-100 text-gray-500 text-xs rounded-full">{channel_signals?.length}개 채널</span>
          <span className="text-xs text-gray-400 ml-auto">내부 채널 (이커머스) + 외부 여론 채널</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {channel_signals?.map((signal, idx) => {
            const cfg = PLATFORM_CONFIG[signal.platform] || {
              icon: MessageSquare,
              color: 'border-gray-200 bg-gray-50',
              badge: 'bg-gray-100 text-gray-600',
              label: signal.data_type,
              type: '채널',
              typeColor: 'bg-gray-100 text-gray-600',
            };
            const Icon = cfg.icon;
            return (
              <div key={idx} className={`border-2 rounded-xl p-4 ${cfg.color}`}>
                {/* Header */}
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Icon size={16} className="text-gray-600" />
                    <span className="text-sm font-bold text-gray-800">{signal.platform}</span>
                  </div>
                  <div className="flex items-center gap-1.5 flex-wrap justify-end">
                    {signal.viral_risk && <ViralRiskBadge risk={signal.viral_risk} />}
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cfg.typeColor}`}>
                      {cfg.type}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${cfg.badge}`}>
                      {cfg.label}
                    </span>
                  </div>
                </div>

                {/* Content */}
                <p className="text-xs text-gray-700 leading-relaxed line-clamp-3 mb-2">
                  &ldquo;{signal.content}&rdquo;
                </p>

                {/* Risk Indicators */}
                <div className="flex flex-wrap gap-1">
                  {signal.risk_indicators?.map((ind, i) => (
                    <span
                      key={i}
                      className="text-xs px-2 py-0.5 bg-red-100 text-red-700 rounded-full font-medium"
                    >
                      ⚠ {ind}
                    </span>
                  ))}
                </div>

                {/* Metadata */}
                {signal.metadata && (
                  <p className="text-xs text-gray-400 mt-2">
                    {signal.metadata.rating && `★ ${signal.metadata.rating}/5 · `}
                    {signal.metadata.likes && `좋아요 ${signal.metadata.likes} · `}
                    {signal.metadata.visitor_count && `조회 ${signal.metadata.visitor_count.toLocaleString()} · `}
                    {signal.metadata.view_count && `뷰 ${signal.metadata.view_count.toLocaleString()} · `}
                    {new Date(signal.metadata.timestamp).toLocaleDateString('ko-KR')}
                  </p>
                )}

                {/* Comment Growth Chart */}
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
