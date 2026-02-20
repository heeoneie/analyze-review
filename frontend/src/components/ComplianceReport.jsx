import { FileCheck, Loader2, AlertTriangle } from 'lucide-react';

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

const ASSESSMENT_LABELS = {
  legal: '법적 리스크',
  reputation: '평판 리스크',
  operational: '운영 리스크',
  safety: '안전 리스크',
};

const SEVERITY_BORDER = {
  critical: 'border-l-red-500',
  high:     'border-l-red-700',
  medium:   'border-l-amber-600',
  low:      'border-l-slate-600',
};

export default function ComplianceReport({ data, loading, error, onGenerate }) {
  return (
    <div className="bg-slate-900 rounded-2xl border border-slate-800 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <FileCheck className="text-slate-400" size={20} />
          <h3 className="text-base font-bold text-white">컴플라이언스 보고서</h3>
        </div>
        {!data && !loading && (
          <button
            onClick={onGenerate}
            className="px-3 py-1.5 text-sm bg-slate-800 text-slate-300 rounded-lg hover:bg-slate-700 transition-colors border border-slate-700"
          >
            보고서 생성
          </button>
        )}
      </div>

      {error && (
        <div className="bg-red-950 text-red-400 border border-red-800 rounded-lg px-4 py-2 text-sm mb-4">{error}</div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64 text-slate-500">
          <Loader2 className="animate-spin mr-2" size={20} />
          보고서 생성 중...
        </div>
      ) : data ? (
        <div className="space-y-4">
          {/* Risk Level Badge */}
          <div className="flex items-center gap-3">
            <span className={`px-3 py-1 rounded-full text-xs font-semibold ${RISK_LEVEL_STYLES[data.overall_risk_level] || 'bg-slate-800 text-slate-400'}`}>
              {data.overall_risk_level}
            </span>
            {data.report_date && (
              <span className="text-xs text-slate-500">{data.report_date}</span>
            )}
          </div>

          {/* Monitoring Summary */}
          {data.monitoring_summary && (
            <p className="text-sm text-slate-300 bg-slate-800 rounded-lg p-3 leading-relaxed border border-slate-700">
              {data.monitoring_summary}
            </p>
          )}

          {/* Monitored Channels */}
          {data.monitored_channels?.length > 0 && (
            <div className="space-y-1.5">
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">채널별 모니터링 현황</h4>
              {data.monitored_channels.map((ch, idx) => (
                <div key={idx} className="flex items-center justify-between bg-slate-800 rounded-lg px-3 py-2 border border-slate-700">
                  <div className="flex items-center gap-2">
                    <span className={`w-1.5 h-1.5 rounded-full ${ch.status === 'active' ? 'bg-emerald-400' : 'bg-slate-600'}`} />
                    <span className="text-xs text-slate-300">{ch.channel}</span>
                  </div>
                  <div className="flex items-center gap-3 text-xs">
                    <span className="text-slate-500">{ch.feed_count?.toLocaleString()}건</span>
                    {ch.risk_count > 0 && (
                      <span className="text-red-400 font-medium">리스크 {ch.risk_count}건</span>
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
                <div key={key} className="bg-slate-800 rounded-lg p-3 border border-slate-700">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-slate-400">
                      {ASSESSMENT_LABELS[key] || key}
                    </span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${ASSESSMENT_LEVEL_STYLES[val.level] || 'bg-slate-700 text-slate-400'}`}>
                      {val.level?.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 leading-relaxed">{val.description}</p>
                </div>
              ))}
            </div>
          )}

          {/* Risk Events */}
          {data.risk_events?.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-slate-400 flex items-center gap-1 uppercase tracking-wide">
                <AlertTriangle size={12} />감지된 리스크 이벤트
              </h4>
              {data.risk_events.map((event, idx) => (
                <div
                  key={event.id || idx}
                  className={`border-l-4 ${SEVERITY_BORDER[event.severity] || 'border-l-slate-600'} bg-slate-800 rounded-r-lg p-3 border border-slate-700 border-l-0`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-semibold text-slate-200">{event.category}</span>
                    {event.channel && (
                      <span className="text-xs text-slate-500">[{event.channel}]</span>
                    )}
                    {event.affected_count && (
                      <span className="text-xs text-slate-500">영향 {event.affected_count}건</span>
                    )}
                  </div>
                  <p className="text-xs text-slate-400">{event.description}</p>
                  {event.recommended_action && (
                    <p className="text-xs text-slate-300 mt-1">→ {event.recommended_action}</p>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Next Actions */}
          {data.next_actions?.length > 0 && (
            <div className="bg-slate-800 rounded-lg p-3 border border-slate-700">
              <h4 className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wide">다음 조치사항</h4>
              <ul className="space-y-1">
                {data.next_actions.map((action, idx) => (
                  <li key={idx} className="text-xs text-slate-300 flex items-start gap-1.5">
                    <span className="mt-0.5 text-slate-500">→</span>
                    {action}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : (
        <div className="flex items-center justify-center h-64 text-slate-600 text-sm">
          보고서를 생성하려면 버튼을 클릭하세요
        </div>
      )}
    </div>
  );
}
