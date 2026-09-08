import { useCallback, useEffect, useRef, useState } from 'react';
import { Loader2, Sparkles, Square } from 'lucide-react';
import { generateRepliesBatch, getPendingReplies } from '../api/client';

// 한 요청이 처리할 건수. 서버 기본값과 맞춘다. 크게 잡으면 한 번에 오래
// 걸려 진행률이 안 움직이고, 작게 잡으면 왕복이 잦아진다.
const BATCH = 5;

export default function BulkReplyBar({ refreshKey, onProgress, onUnauthorized }) {
  const [pending, setPending] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [done, setDone] = useState(0);
  const [failed, setFailed] = useState(0);
  const [error, setError] = useState(null);
  // 사장님이 멈추면 다음 묶음을 부르지 않는다. 이미 나간 요청은 끝난다.
  const stopped = useRef(false);

  const loadPending = useCallback(async () => {
    try {
      const { data } = await getPendingReplies();
      setPending(data.pending);
    } catch (err) {
      if (err.response?.status === 401) onUnauthorized?.();
    }
  }, [onUnauthorized]);

  useEffect(() => { loadPending(); }, [refreshKey, loadPending]);

  const run = async () => {
    stopped.current = false;
    setIsRunning(true);
    setError(null);
    setDone(0);
    setFailed(0);

    try {
      // 남은 게 없을 때까지 이어서 부른다. 한 요청에 다 몰면 몇 분이 걸려
      // 브라우저가 먼저 끊는다.
      for (;;) {
        const { data } = await generateRepliesBatch(BATCH);
        setDone((n) => n + data.generated);
        setFailed((n) => n + data.failed);
        setPending(data.remaining);
        onProgress?.();
        if (stopped.current || data.remaining === 0) break;
        // 아무것도 못 만들었는데 남아 있다면 계속 불러도 같은 결과다.
        if (data.generated === 0 && data.failed === 0) break;
      }
    } catch (err) {
      if (err.response?.status === 401) onUnauthorized?.();
      else {
        setError(
          err.response?.data?.detail
          || '답글을 만들지 못했습니다. 잠시 후 다시 시도해 주세요.',
        );
      }
    } finally {
      setIsRunning(false);
    }
  };

  if (!pending && !isRunning && !done) return null;

  return (
    <div className="rounded-2xl bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-700">
            {isRunning
              ? `답글 만드는 중 · ${done}개 완료, ${pending}개 남음`
              : pending > 0
                ? `답글이 없는 리뷰 ${pending}개`
                : `${done}개를 만들었습니다`}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {isRunning
              ? '창을 닫아도 만들어진 답글은 남습니다.'
              : '아쉬운 리뷰부터 만듭니다. 만든 답글은 아래 목록에서 확인하고 고치실 수 있습니다.'}
          </p>
        </div>

        {isRunning ? (
          <button
            type="button"
            onClick={() => { stopped.current = true; }}
            className="flex shrink-0 items-center justify-center gap-2 rounded-xl border
                       border-slate-200 px-5 py-3 text-sm font-semibold text-slate-600
                       hover:border-slate-300"
          >
            <Square size={15} />
            여기까지
          </button>
        ) : (
          pending > 0 && (
            <button
              type="button"
              onClick={run}
              className="flex shrink-0 items-center justify-center gap-2 rounded-xl
                         bg-slate-900 px-5 py-3 text-sm font-semibold text-white
                         transition hover:bg-slate-700"
            >
              <Sparkles size={15} />
              전체 답글 만들기
            </button>
          )
        )}
      </div>

      {isRunning && (
        <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
          <Loader2 size={13} className="animate-spin" />
          리뷰 한 건마다 따로 만들기 때문에 시간이 걸립니다.
        </div>
      )}

      {failed > 0 && !isRunning && (
        <p className="mt-3 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-800">
          {failed}개는 만들지 못했습니다. 다시 누르면 그 리뷰만 다시 시도합니다.
        </p>
      )}

      {error && (
        <p className="mt-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
      )}
    </div>
  );
}
