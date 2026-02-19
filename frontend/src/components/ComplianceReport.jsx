import { FileCheck, Loader2, AlertTriangle } from 'lucide-react';

const RISK_LEVEL_STYLES = {
  '안전': 'bg-green-100 text-green-700',
  '주의': 'bg-yellow-100 text-yellow-700',
  '경고': 'bg-orange-100 text-orange-700',
  '위험': 'bg-red-100 text-red-700',
};

const ASSESSMENT_LEVEL_STYLES = {
  low: 'bg-green-100 text-green-700',
  medium: 'bg-yellow-100 text-yellow-700',
  high: 'bg-red-100 text-red-700',
};

const ASSESSMENT_LABELS = {
  legal: '법적 리스크',
  reputation: '평판 리스크',
  operational: '운영 리스크',
  safety: '안전 리스크',
};

const SEVERITY_STYLES = {
  high: 'border-l-red-500',
  medium: 'border-l-yellow-500',
  low: 'border-l-green-500',
};

export default function ComplianceReport({ data, loading, error, onGenerate }) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <FileCheck className="text-blue-500" size={20} />
          <h3 className="text-lg font-bold text-gray-900">컴플라이언스 보고서</h3>
        </div>
        {!data && !loading && (
          <button
            onClick={onGenerate}
            className="px-4 py-2 text-sm bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition-colors"
          >
            보고서 생성
          </button>
        )}
      </div>

      {error && (
        <div className="bg-red-50 text-red-600 rounded-lg px-4 py-2 text-sm mb-4">{error}</div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64 text-gray-400">
          <Loader2 className="animate-spin mr-2" size={20} />
          보고서 생성 중...
        </div>
      ) : data ? (
        <div className="space-y-4">
          {/* Risk Level Badge */}
          <div className="flex items-center gap-3">
            <span className={`px-3 py-1 rounded-full text-sm font-semibold ${RISK_LEVEL_STYLES[data.overall_risk_level] || 'bg-gray-100 text-gray-600'}`}>
              {data.overall_risk_level}
            </span>
            {data.report_date && (
              <span className="text-xs text-gray-400">{data.report_date}</span>
            )}
          </div>

          {/* Monitoring Summary */}
          {data.monitoring_summary && (
            <p className="text-sm text-gray-700 bg-blue-50 rounded-lg p-3 leading-relaxed">
              {data.monitoring_summary}
            </p>
          )}

          {/* Risk Assessment Grid */}
          {data.risk_assessment && Object.keys(data.risk_assessment).length > 0 && (
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(data.risk_assessment).map(([key, val]) => (
                <div key={key} className="bg-gray-50 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-gray-600">
                      {ASSESSMENT_LABELS[key] || key}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${ASSESSMENT_LEVEL_STYLES[val.level] || 'bg-gray-100 text-gray-500'}`}>
                      {val.level?.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 leading-relaxed">{val.description}</p>
                </div>
              ))}
            </div>
          )}

          {/* Risk Events */}
          {data.risk_events?.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-semibold text-gray-700 flex items-center gap-1">
                <AlertTriangle size={14} />
                감지된 리스크 이벤트
              </h4>
              {data.risk_events.map((event, idx) => (
                <div
                  key={event.id || idx}
                  className={`border-l-4 ${SEVERITY_STYLES[event.severity] || 'border-l-gray-300'} bg-gray-50 rounded-r-lg p-3`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-semibold text-gray-800">{event.category}</span>
                    {event.affected_count && (
                      <span className="text-xs text-gray-400">영향 {event.affected_count}건</span>
                    )}
                  </div>
                  <p className="text-xs text-gray-600">{event.description}</p>
                  {event.recommended_action && (
                    <p className="text-xs text-blue-600 mt-1">→ {event.recommended_action}</p>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Next Actions */}
          {data.next_actions?.length > 0 && (
            <div className="bg-purple-50 rounded-lg p-3">
              <h4 className="text-xs font-semibold text-purple-700 mb-2">다음 조치사항</h4>
              <ul className="space-y-1">
                {data.next_actions.map((action, idx) => (
                  <li key={idx} className="text-xs text-purple-600 flex items-start gap-1.5">
                    <span className="mt-0.5">•</span>
                    {action}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : (
        <div className="flex items-center justify-center h-64 text-gray-300 text-sm">
          보고서를 생성하려면 버튼을 클릭하세요
        </div>
      )}
    </div>
  );
}
