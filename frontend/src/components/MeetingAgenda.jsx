import { CalendarClock, Loader2, Users, Clock } from 'lucide-react';
import { useLang } from '../contexts/LangContext';
import { KO_URGENCY_KEY } from '../i18n';

const URGENCY_STYLES = {
  normal:   'bg-zinc-800 text-zinc-300 border border-zinc-700',
  urgent:   'bg-amber-950 text-amber-400 border border-amber-800',
  critical: 'bg-red-950 text-red-400 border border-red-800',
};

const PRIORITY_BORDER = {
  critical: 'border-l-red-500',
  high:     'border-l-red-700',
  medium:   'border-l-amber-600',
  low:      'border-l-zinc-600',
};

const DEFAULT_ATTENDEE_KEYS = [
  'meeting.att_clo', 'meeting.att_legal', 'meeting.att_lawyer1',
  'meeting.att_lawyer2', 'meeting.att_pr', 'meeting.att_ceo',
];

export default function MeetingAgenda({ data, loading, error, onGenerate }) {
  const { t } = useLang();

  const urgencyKey = data ? (KO_URGENCY_KEY[data.urgency] || 'urgent') : 'urgent';

  return (
    <div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <CalendarClock className="text-zinc-400" size={20} />
          <h3 className="text-base font-bold text-white">{t('meeting.title')}</h3>
        </div>
        {!data && !loading && (
          <button
            onClick={onGenerate}
            className="px-3 py-1.5 text-sm bg-zinc-800 text-zinc-300 rounded-lg hover:bg-zinc-700 transition-colors border border-zinc-700"
          >
            {t('meeting.generate')}
          </button>
        )}
      </div>

      {error && (
        <div className="bg-red-950 text-red-400 border border-red-800 rounded-lg px-4 py-2 text-sm mb-4">{error}</div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64 text-zinc-500">
          <Loader2 className="animate-spin mr-2" size={20} />
          {t('meeting.generating')}
        </div>
      ) : data ? (
        <div className="space-y-4">
          {/* Title + Urgency */}
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h4 className="text-sm font-bold text-white">{data.meeting_title}</h4>
              <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${URGENCY_STYLES[urgencyKey] || URGENCY_STYLES.urgent}`}>
                {t('meeting.' + urgencyKey)}
              </span>
            </div>
            {data.estimated_duration && (
              <div className="flex items-center gap-1 text-xs text-zinc-500">
                <Clock size={12} />
                {t('meeting.estimated')} {data.estimated_duration}
              </div>
            )}
          </div>

          {/* Attendees */}
          <div>
            <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-wide flex items-center gap-1 mb-2">
              <Users size={11} />{t('meeting.attendees')}
            </h4>
            <div className="flex flex-wrap gap-1.5">
              {DEFAULT_ATTENDEE_KEYS.map((key, idx) => (
                <span
                  key={idx}
                  className="px-2 py-1 bg-amber-950/50 border border-amber-800/60 rounded-lg text-xs text-amber-300"
                >
                  {t(key)}
                </span>
              ))}
            </div>
          </div>

          {/* Agenda Items */}
          {data.agenda_items?.length > 0 && (
            <div className="space-y-2.5">
              {data.agenda_items.map((item, idx) => (
                <div
                  key={idx}
                  className={`border-l-4 ${PRIORITY_BORDER[item.priority] || 'border-l-zinc-600'} bg-zinc-800 rounded-r-lg p-3 border border-zinc-700 border-l-0`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="w-5 h-5 bg-zinc-700 text-zinc-300 rounded-full flex items-center justify-center text-xs font-bold">
                        {item.order || idx + 1}
                      </span>
                      <span className="text-sm font-semibold text-zinc-200">{item.title}</span>
                    </div>
                    {item.duration && (
                      <span className="text-xs text-zinc-500">{item.duration}</span>
                    )}
                  </div>

                  {item.presenter && (
                    <p className="text-xs text-zinc-500 mb-1.5">{t('meeting.presenter')} {item.presenter}</p>
                  )}

                  {/* Discussion Points */}
                  {item.discussion_points?.length > 0 && (
                    <ul className="space-y-0.5 mb-2">
                      {item.discussion_points.map((point, pidx) => (
                        <li key={pidx} className="text-xs text-zinc-400 flex items-start gap-1.5">
                          <span className="mt-0.5 text-zinc-600">–</span>
                          {point}
                        </li>
                      ))}
                    </ul>
                  )}

                  {/* Action Items */}
                  {item.action_items?.length > 0 && (
                    <div className="bg-zinc-900 rounded-lg p-2 space-y-1 border border-zinc-700">
                      {item.action_items.map((ai, aidx) => (
                        <div key={aidx} className="flex items-center justify-between text-xs">
                          <span className="text-zinc-300">{ai.task}</span>
                          <div className="flex items-center gap-2 text-zinc-500 flex-shrink-0">
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
            <div className="bg-zinc-800 rounded-lg p-3 border border-zinc-700">
              <h4 className="text-xs font-semibold text-zinc-400 mb-2 uppercase tracking-wide">{t('meeting.preparation')}</h4>
              <ul className="space-y-1">
                {data.preparation.map((item, idx) => (
                  <li key={idx} className="text-xs text-zinc-300 flex items-start gap-1.5">
                    <span className="mt-0.5 text-zinc-500">•</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : (
        <div className="flex items-center justify-center h-64 text-zinc-600 text-sm">
          {t('meeting.empty')}
        </div>
      )}
    </div>
  );
}
