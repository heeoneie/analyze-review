import { FileCheck, Loader2, AlertTriangle } from 'lucide-react';
import { useLang } from '../contexts/LangContext';
import { KO_RISK_KEY, KO_ASSESSMENT_KEY } from '../i18n';

const RISK_LEVEL_STYLES = {
  '안전': 'bg-emerald-950 text-emerald-400 border border-emerald-800',
  '주의': 'bg-amber-950 text-amber-400 border border-amber-800',
  '경고': 'bg-orange-950 text-orange-400 border border-orange-800',
  '위험': 'bg-red-950 text-red-400 border border-red-800',
};

const ASSESSMENT_LEVEL_STYLES = {
  low:    'bg-emerald-950 text-emerald-400',
  medium: 'bg-amber-950 text-amber-400',
  high:   'bg-red-950 text-red-400',
};

const SEVERITY_BORDER = {
  critical: 'border-l-red-500',
  high:     'border-l-red-700',
  medium:   'border-l-amber-600',
  low:      'border-l-zinc-600',
};

export default function ComplianceReport({ data, loading, error, onGenerate }) {
  const { t } = useLang();

  return (
    <div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <FileCheck className="text-zinc-400" size={20} />
          <h3 className="text-base font-bold text-white">{t('compliance.title')}</h3>
        </div>
        {!data && !loading && (
          <button
            onClick={onGenerate}
            className="px-3 py-1.5 text-sm bg-zinc-800 text-zinc-300 rounded-lg hover:bg-zinc-700 transition-colors border border-zinc-700"
          >
            {t('compliance.generate')}
          </button>
        )}
      </div>

      {error && (
        <div className="bg-red-950 text-red-400 border border-red-800 rounded-lg px-4 py-2 text-sm mb-4">{error}</div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64 text-zinc-500">
          <Loader2 className="animate-spin mr-2" size={20} />
          {t('compliance.generating')}
        </div>
      ) : data ? (
        <div className="space-y-4">
          {/* Risk Level Badge */}
          <div className="flex items-center gap-3">
            <span className={`px-3 py-1 rounded-full text-xs font-semibold ${RISK_LEVEL_STYLES[data.overall_risk_level] || 'bg-zinc-800 text-zinc-400'}`}>
              {t('compliance.' + (KO_RISK_KEY[data.overall_risk_level] || 'caution'))}
            </span>
            {data.report_date && (
              <span className="text-xs text-zinc-500">{data.report_date}</span>
            )}
          </div>

          {/* Monitoring Summary */}
          {data.monitoring_summary && (
            <p className="text-sm text-zinc-300 bg-zinc-800 rounded-lg p-3 leading-relaxed border border-zinc-700">
              {data.monitoring_summary}
            </p>
          )}

          {/* Monitored Channels */}
          {data.monitored_channels?.length > 0 && (
            <div className="space-y-1.5">
              <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-wide">{t('compliance.channelStatus')}</h4>
              {data.monitored_channels.map((ch, idx) => (
                <div key={idx} className="flex items-center justify-between bg-zinc-800 rounded-lg px-3 py-2 border border-zinc-700">
                  <div className="flex items-center gap-2">
                    <span className={`w-1.5 h-1.5 rounded-full ${ch.status === 'active' ? 'bg-emerald-400' : 'bg-zinc-600'}`} />
                    <span className="text-xs text-zinc-300">{ch.channel}</span>
                  </div>
                  <div className="flex items-center gap-3 text-xs">
                    <span className="text-zinc-500">{ch.feed_count?.toLocaleString()}{t('compliance.count')}</span>
                    {ch.risk_count > 0 && (
                      <span className="text-red-400 font-medium">{t('compliance.riskCount')} {ch.risk_count}{t('compliance.count')}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Risk Assessment Grid */}
          {data.risk_assessment && Object.keys(data.risk_assessment).length > 0 && (
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(data.risk_assessment).map(([key, val]) => (
                <div key={key} className="bg-zinc-800 rounded-lg p-3 border border-zinc-700">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-zinc-400">
                      {t('compliance.' + (KO_ASSESSMENT_KEY[key] || key))}
                    </span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${ASSESSMENT_LEVEL_STYLES[val.level] || 'bg-zinc-700 text-zinc-400'}`}>
                      {val.level?.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-xs text-zinc-500 leading-relaxed">{val.description}</p>
                </div>
              ))}
            </div>
          )}

          {/* Risk Events */}
          {data.risk_events?.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-zinc-400 flex items-center gap-1 uppercase tracking-wide">
                <AlertTriangle size={12} />{t('compliance.detectedEvents')}
              </h4>
              {data.risk_events.map((event, idx) => (
                <div
                  key={event.id || idx}
                  className={`border-l-4 ${SEVERITY_BORDER[event.severity] || 'border-l-zinc-600'} bg-zinc-800 rounded-r-lg p-3 border border-zinc-700 border-l-0`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-semibold text-zinc-200">{event.category}</span>
                    {event.channel && (
                      <span className="text-xs text-zinc-500">[{event.channel}]</span>
                    )}
                    {event.affected_count && (
                      <span className="text-xs text-zinc-500">{t('compliance.affected')} {event.affected_count}{t('compliance.count')}</span>
                    )}
                  </div>
                  <p className="text-xs text-zinc-400">{event.description}</p>
                  {event.recommended_action && (
                    <p className="text-xs text-zinc-300 mt-1">→ {event.recommended_action}</p>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Next Actions */}
          {data.next_actions?.length > 0 && (
            <div className="bg-zinc-800 rounded-lg p-3 border border-zinc-700">
              <h4 className="text-xs font-semibold text-zinc-400 mb-2 uppercase tracking-wide">{t('compliance.nextActions')}</h4>
              <ul className="space-y-1">
                {data.next_actions.map((action, idx) => (
                  <li key={idx} className="text-xs text-zinc-300 flex items-start gap-1.5">
                    <span className="mt-0.5 text-zinc-500">→</span>
                    {action}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Audit Log Footer */}
          <div className="flex items-center justify-between pt-2 border-t border-zinc-800">
            <div className="flex items-center gap-1.5">
              <span className="relative flex h-1.5 w-1.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-40" />
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-400" />
              </span>
              <span className="text-[11px] font-semibold text-emerald-500 uppercase tracking-widest">{t('compliance.auditLog')}</span>
            </div>
            <div className="flex items-center gap-3 text-[11px] text-zinc-600">
              <span>{t('compliance.auditLastRecord')}</span>
              <span className="text-zinc-700">·</span>
              <span>{t('compliance.auditTotal')}</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-center h-64 text-zinc-600 text-sm">
          {t('compliance.empty')}
        </div>
      )}
    </div>
  );
}
