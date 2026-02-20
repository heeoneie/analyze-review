import { CalendarClock, Loader2, Users, Clock } from 'lucide-react';

const URGENCY_STYLES = {
  '일반':   'bg-slate-800 text-slate-300 border border-slate-700',
  '긴급':   'bg-amber-950 text-amber-400 border border-amber-800',
  '초긴급': 'bg-red-950 text-red-400 border border-red-800',
};

const PRIORITY_BORDER = {
  critical: 'border-l-red-500',
  high:     'border-l-red-700',
  medium:   'border-l-amber-600',
  low:      'border-l-slate-600',
};

export default function MeetingAgenda({ data, loading, error, onGenerate }) {
  return (
    <div className="bg-slate-900 rounded-2xl border border-slate-800 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <CalendarClock className="text-slate-400" size={20} />
          <h3 className="text-base font-bold text-white">회의 안건</h3>
        </div>
        {!data && !loading && (
          <button
            onClick={onGenerate}
            className="px-3 py-1.5 text-sm bg-slate-800 text-slate-300 rounded-lg hover:bg-slate-700 transition-colors border border-slate-700"
          >
            안건 생성
          </button>
        )}
      </div>

      {error && (
        <div className="bg-red-950 text-red-400 border border-red-800 rounded-lg px-4 py-2 text-sm mb-4">{error}</div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64 text-slate-500">
          <Loader2 className="animate-spin mr-2" size={20} />
          회의 안건 생성 중...
        </div>
      ) : data ? (
        <div className="space-y-4">
          {/* Title + Urgency */}
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h4 className="text-sm font-bold text-white">{data.meeting_title}</h4>
              <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${URGENCY_STYLES[data.urgency] || 'bg-slate-800 text-slate-400'}`}>
                {data.urgency}
              </span>
            </div>
            {data.estimated_duration && (
              <div className="flex items-center gap-1 text-xs text-slate-500">
                <Clock size={12} />
                예상 소요: {data.estimated_duration}
              </div>
            )}
          </div>

          {/* Attendees */}
          {data.attendees?.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide flex items-center gap-1 mb-2">
                <Users size={11} />참석 대상
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {data.attendees.map((att, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-1 bg-slate-800 border border-slate-700 rounded-lg text-xs text-slate-300"
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
            <div className="space-y-2.5">
              {data.agenda_items.map((item, idx) => (
                <div
                  key={idx}
                  className={`border-l-4 ${PRIORITY_BORDER[item.priority] || 'border-l-slate-600'} bg-slate-800 rounded-r-lg p-3 border border-slate-700 border-l-0`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="w-5 h-5 bg-slate-700 text-slate-300 rounded-full flex items-center justify-center text-xs font-bold">
                        {item.order || idx + 1}
                      </span>
                      <span className="text-sm font-semibold text-slate-200">{item.title}</span>
                    </div>
                    {item.duration && (
                      <span className="text-xs text-slate-500">{item.duration}</span>
                    )}
                  </div>

                  {item.presenter && (
                    <p className="text-xs text-slate-500 mb-1.5">발표: {item.presenter}</p>
                  )}

                  {/* Discussion Points */}
                  {item.discussion_points?.length > 0 && (
                    <ul className="space-y-0.5 mb-2">
                      {item.discussion_points.map((point, pidx) => (
                        <li key={pidx} className="text-xs text-slate-400 flex items-start gap-1.5">
                          <span className="mt-0.5 text-slate-600">–</span>
                          {point}
                        </li>
                      ))}
                    </ul>
                  )}

                  {/* Action Items */}
                  {item.action_items?.length > 0 && (
                    <div className="bg-slate-900 rounded-lg p-2 space-y-1 border border-slate-700">
                      {item.action_items.map((ai, aidx) => (
                        <div key={aidx} className="flex items-center justify-between text-xs">
                          <span className="text-slate-300">{ai.task}</span>
                          <div className="flex items-center gap-2 text-slate-500 flex-shrink-0">
                            <span>{ai.owner}</span>
                            <span className="text-amber-400 font-medium">{ai.deadline}</span>
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
            <div className="bg-slate-800 rounded-lg p-3 border border-slate-700">
              <h4 className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wide">사전 준비사항</h4>
              <ul className="space-y-1">
                {data.preparation.map((item, idx) => (
                  <li key={idx} className="text-xs text-slate-300 flex items-start gap-1.5">
                    <span className="mt-0.5 text-slate-500">•</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : (
        <div className="flex items-center justify-center h-64 text-slate-600 text-sm">
          회의 안건을 생성하려면 버튼을 클릭하세요
        </div>
      )}
    </div>
  );
}
