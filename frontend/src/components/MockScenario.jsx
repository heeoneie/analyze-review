import { AlertTriangle, ShoppingCart, Youtube, PenSquare, MessageSquare, TrendingUp } from 'lucide-react';
import { useLang } from '../contexts/LangContext';

const PLATFORM_CONFIG = {
  'Coupang': { icon: ShoppingCart, labelKey: 'risk.chEcommerce' },
  'YouTube': { icon: Youtube,      labelKey: 'risk.chYoutube' },
  'Naver Blog': { icon: PenSquare, labelKey: 'risk.chNaver' },
  'Community (뽐뿌)': { icon: MessageSquare, labelKey: 'risk.chCommunity' },
};

const VIRAL_KEY = { '높음': 'high', '보통': 'medium', '낮음': 'low' };

function ViralRiskBadge({ risk }) {
  const { t } = useLang();
  const key = VIRAL_KEY[risk] || 'low';
  const STYLE = {
    high:   { cls: 'bg-red-950 text-red-400 border border-red-800',     dot: 'bg-red-500',   pulse: true },
    medium: { cls: 'bg-amber-950 text-amber-400 border border-amber-800', dot: 'bg-amber-400', pulse: false },
    low:    { cls: 'bg-zinc-800 text-zinc-400 border border-zinc-700',   dot: 'bg-zinc-500',  pulse: false },
  };
  const cfg = STYLE[key];
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold ${cfg.cls}`}>
      <span className="relative flex h-1.5 w-1.5">
        {cfg.pulse && (
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${cfg.dot} opacity-60`} />
        )}
        <span className={`relative inline-flex rounded-full h-1.5 w-1.5 ${cfg.dot}`} />
      </span>
      {t('mock.viralRisk')} {t(`mock.${key}`)}
    </span>
  );
}

function CommentGrowthChart({ growth, metricLabel }) {
  const { t } = useLang();
  if (!growth?.length) return null;

  const max = Math.max(1, ...growth.map((p) => p.delta));
  const MAX_H = 28;

  const first = growth[0].delta;
  const last = growth[growth.length - 1].delta;
  const ratio = last / (first || 1);
  const trend =
    ratio >= 3
      ? { label: t('mock.surging'),    cls: 'text-red-400 font-bold' }
      : ratio >= 1.8
      ? { label: t('mock.increasing'), cls: 'text-amber-400 font-semibold' }
      : { label: t('mock.steady'),     cls: 'text-zinc-500' };

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] font-medium text-zinc-500 flex items-center gap-1">
          <TrendingUp size={11} />
          {metricLabel || t('mock.reaction')} {t('mock.trendInterval')}
        </span>
        <span className={`text-[11px] ${trend.cls}`}>{trend.label}</span>
      </div>
      <div className="flex items-end gap-3">
        {growth.map((point, i) => {
          const barH = Math.max(4, Math.round((point.delta / max) * MAX_H));
          const isLast = i === growth.length - 1;
          return (
            <div key={i} className="flex flex-col items-center gap-0.5">
              <span className={`text-[11px] font-bold ${isLast ? 'text-red-400' : 'text-zinc-400'}`}>
                +{point.delta.toLocaleString()}
              </span>
              <div
                className={`w-5 rounded-t ${isLast ? 'bg-red-600' : 'bg-zinc-600'}`}
                style={{ height: `${barH}px` }}
              />
              <span className="text-[10px] text-zinc-600 mt-0.5">{point.t}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function MockScenario({ data }) {
  const { t } = useLang();
  if (!data) return null;

  const { risk_level, incident_title, incident_summary, clustering_reason, channel_signals } = data;

  const alertBorder =
    risk_level === 'RED' ? 'border-red-800 bg-red-950/40' :
    risk_level === 'ORANGE' ? 'border-orange-800 bg-orange-950/40' :
    'border-amber-800 bg-amber-950/40';

  const riskLabel =
    risk_level === 'RED' ? t('mock.criticalRisk') :
    risk_level === 'ORANGE' ? t('mock.warningRisk') :
    t('mock.cautionRisk');

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
                {riskLabel}
              </span>
            </div>
            <p className="text-sm text-zinc-300 leading-relaxed">{incident_summary}</p>
            {clustering_reason && (
              <p className="text-xs text-zinc-500 mt-2 bg-zinc-900/60 rounded-lg px-3 py-1.5 border border-zinc-800">
                🔗 {clustering_reason}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Channel Signals */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <span className="text-sm font-semibold text-zinc-200">{t('mock.detectedSignals')}</span>
          <span className="px-2 py-0.5 bg-zinc-800 text-zinc-400 text-xs rounded-full border border-zinc-700">
            {channel_signals?.length ?? 0}{t('mock.channels')}
          </span>
          <span className="text-xs text-zinc-600 ml-auto">{t('mock.internalExternal')}</span>
        </div>
        <div className="grid grid-cols-1 gap-3">
          {channel_signals?.map((signal, idx) => {
            const cfg = PLATFORM_CONFIG[signal.platform];
            const Icon = cfg?.icon ?? MessageSquare;
            const labelText = cfg ? t(cfg.labelKey) : signal.data_type;
            const typeText = signal.channel_type === 'internal' ? t('mock.internal') : t('mock.external');

            return (
              <div key={idx} className="border border-zinc-700 bg-zinc-900 rounded-xl p-4">
                {/* Header */}
                <div className="flex items-center justify-between mb-2.5">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 bg-zinc-800 rounded-lg flex items-center justify-center">
                      <Icon size={14} className="text-zinc-400" />
                    </div>
                    <span className="text-sm font-semibold text-zinc-200">{signal.platform}</span>
                  </div>
                  <div className="flex items-center gap-1.5 flex-wrap justify-end">
                    {signal.viral_risk && <ViralRiskBadge risk={signal.viral_risk} />}
                    <span className="text-[11px] px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400 border border-zinc-700">
                      {typeText}
                    </span>
                    <span className="text-[11px] px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400 border border-zinc-700">
                      {labelText}
                    </span>
                  </div>
                </div>

                {/* Body: 좌(콘텐츠) + 우(바 차트) */}
                <div className="flex gap-4 items-start">
                  {/* Left */}
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-zinc-400 leading-relaxed line-clamp-3 mb-2.5">
                      &ldquo;{signal.content}&rdquo;
                    </p>
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
                    {signal.metadata && (
                      <p className="text-[11px] text-zinc-600 mt-2">
                        {signal.metadata.rating != null && `★ ${signal.metadata.rating}/5 · `}
                        {signal.metadata.likes != null && `👍 ${signal.metadata.likes} · `}
                        {signal.metadata.visitor_count != null && `👁 ${signal.metadata.visitor_count.toLocaleString()} · `}
                        {signal.metadata.view_count != null && `👁 ${signal.metadata.view_count.toLocaleString()} · `}
                        {signal.metadata.timestamp && !isNaN(new Date(signal.metadata.timestamp))
                          ? new Date(signal.metadata.timestamp).toLocaleDateString('ko-KR')
                          : ''}
                      </p>
                    )}
                  </div>

                  {/* Right: bar chart */}
                  {signal.comment_growth?.length > 0 && (
                    <div className="flex-shrink-0 border-l border-zinc-700 pl-4">
                      <CommentGrowthChart
                        growth={signal.comment_growth}
                        metricLabel={signal.metric_label}
                      />
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
