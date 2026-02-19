import { CalendarClock, Loader2, Users, Clock } from 'lucide-react';

const URGENCY_STYLES = {
  '일반': 'bg-gray-100 text-gray-600',
  '긴급': 'bg-orange-100 text-orange-700',
  '초긴급': 'bg-red-100 text-red-700',
};

const PRIORITY_BORDER = {
  critical: 'border-l-red-500',
  high: 'border-l-orange-500',
  medium: 'border-l-yellow-500',
  low: 'border-l-green-500',
};

export default function MeetingAgenda({ data, loading, error, onGenerate }) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <CalendarClock className="text-orange-500" size={20} />
          <h3 className="text-lg font-bold text-gray-900">회의 안건</h3>
        </div>
        {!data && !loading && (
          <button
            onClick={onGenerate}
            className="px-4 py-2 text-sm bg-orange-50 text-orange-600 rounded-lg hover:bg-orange-100 transition-colors"
          >
            안건 생성
          </button>
        )}
      </div>

      {error && (
        <div className="bg-red-50 text-red-600 rounded-lg px-4 py-2 text-sm mb-4">{error}</div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64 text-gray-400">
          <Loader2 className="animate-spin mr-2" size={20} />
          회의 안건 생성 중...
        </div>
      ) : data ? (
        <div className="space-y-4">
          {/* Title + Urgency */}
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h4 className="text-sm font-bold text-gray-900">{data.meeting_title}</h4>
              <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${URGENCY_STYLES[data.urgency] || 'bg-gray-100 text-gray-600'}`}>
                {data.urgency}
              </span>
            </div>
            {data.estimated_duration && (
              <div className="flex items-center gap-1 text-xs text-gray-400">
                <Clock size={12} />
                예상 소요: {data.estimated_duration}
              </div>
            )}
          </div>

          {/* Attendees */}
          {data.attendees?.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-gray-600 flex items-center gap-1 mb-2">
                <Users size={12} />
                참석 대상
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {data.attendees.map((att, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-1 bg-gray-100 rounded-lg text-xs text-gray-700"
                    title={att.reason}
                  >
                    {att.department} {att.role}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Agenda Items */}
          {data.agenda_items?.length > 0 && (
            <div className="space-y-3">
              {data.agenda_items.map((item, idx) => (
                <div
                  key={idx}
                  className={`border-l-4 ${PRIORITY_BORDER[item.priority] || 'border-l-gray-300'} bg-gray-50 rounded-r-lg p-3`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="w-5 h-5 bg-gray-200 text-gray-600 rounded-full flex items-center justify-center text-xs font-bold">
                        {item.order || idx + 1}
                      </span>
                      <span className="text-sm font-semibold text-gray-800">{item.title}</span>
                    </div>
                    {item.duration && (
                      <span className="text-xs text-gray-400">{item.duration}</span>
                    )}
                  </div>

                  {item.presenter && (
                    <p className="text-xs text-gray-500 mb-1.5">발표: {item.presenter}</p>
                  )}

                  {/* Discussion Points */}
                  {item.discussion_points?.length > 0 && (
                    <ul className="space-y-0.5 mb-2">
                      {item.discussion_points.map((point, pidx) => (
                        <li key={pidx} className="text-xs text-gray-600 flex items-start gap-1.5">
                          <span className="mt-0.5 text-gray-400">-</span>
                          {point}
                        </li>
                      ))}
                    </ul>
                  )}

                  {/* Action Items */}
                  {item.action_items?.length > 0 && (
                    <div className="bg-white rounded-lg p-2 space-y-1">
                      {item.action_items.map((ai, aidx) => (
                        <div key={aidx} className="flex items-center justify-between text-xs">
                          <span className="text-gray-700">{ai.task}</span>
                          <div className="flex items-center gap-2 text-gray-400 flex-shrink-0">
                            <span>{ai.owner}</span>
                            <span className="text-orange-500 font-medium">{ai.deadline}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Preparation */}
          {data.preparation?.length > 0 && (
            <div className="bg-orange-50 rounded-lg p-3">
              <h4 className="text-xs font-semibold text-orange-700 mb-2">사전 준비사항</h4>
              <ul className="space-y-1">
                {data.preparation.map((item, idx) => (
                  <li key={idx} className="text-xs text-orange-600 flex items-start gap-1.5">
                    <span className="mt-0.5">•</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : (
        <div className="flex items-center justify-center h-64 text-gray-300 text-sm">
          회의 안건을 생성하려면 버튼을 클릭하세요
        </div>
      )}
    </div>
  );
}
