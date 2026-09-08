import { useState } from 'react';
import { Sparkles, Copy, RefreshCw, Check, MessageCircle } from 'lucide-react';
import { generateStoreReply, finalizeStoreReply } from '../api/client';

/**
 * 리뷰 한 건에 대한 답글 패널.
 *
 * 매장 경로(`/reply/store/generate`)를 쓴다. 예전에는 `/reply/generate` 를
 * 불렀는데 그건 매장을 모르는 옛 엔드포인트라, 사장님 말투도 쓰지 않고
 * 답글 이력도 남기지 않았다. 붙여넣기 화면에서만 학습이 걸리고 대시보드로
 * 일하는 사장님은 학습이 영영 시작되지 않았다.
 *
 * 복사하면 게시한 것으로 기록한다. 사장님이 실제로 쓰기로 한 문장만
 * 말투 학습의 재료가 된다.
 */
export default function ReplyPanel({ review, onClose, onUnauthorized }) {
  const [result, setResult] = useState(null);
  const [editedReply, setEditedReply] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState(null);

  const generate = async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const { data } = await generateStoreReply({
        review_text: review.Reviews,
        rating: Number(review.Ratings) || 5,
        menu: '',
        // 이 답글이 어느 리뷰 것인지 남긴다. 목록이 "답글 있음" 을 알아야 한다.
        review_id: review.id ?? null,
        // 앞서 만든 문장을 넘겨 같은 첫 문장이 반복되지 않게 한다.
        avoid_openings: result?.opening_sentence ? [result.opening_sentence] : [],
        avoid_closings: result?.closing_sentence ? [result.closing_sentence] : [],
      });
      setResult(data);
      setEditedReply(data.reply);
    } catch (err) {
      if (err.response?.status === 401) onUnauthorized?.();
      else {
        setError(
          err.response?.data?.detail
          || '답글을 만들지 못했습니다. 잠시 후 다시 시도해 주세요.',
        );
      }
    } finally {
      setIsGenerating(false);
    }
  };

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(editedReply);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // 클립보드를 막아 둔 브라우저도 있다. 답글은 화면에 그대로 보인다.
      return;
    }
    // 복사했다는 건 사장님이 이 답글을 쓰기로 했다는 뜻이다. 고쳐 쓴
    // 문장이 있으면 그쪽이 기록된다 — 말투 학습에 더 값진 신호다.
    if (result?.sample_id) {
      finalizeStoreReply(result.sample_id, editedReply).catch(() => {});
    }
  };

  return (
    <div className="mt-3 space-y-4 border-t border-slate-200 pt-4">
      {!result && !isGenerating && (
        <button
          type="button"
          onClick={generate}
          className="flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm
                     font-medium text-white transition hover:bg-slate-700"
        >
          <Sparkles size={16} />
          사장님 말투로 답글 만들기
        </button>
      )}

      {isGenerating && (
        <div className="flex items-center gap-3 py-4">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-900
                          border-t-transparent" />
          <span className="text-sm text-slate-600">답글 만드는 중...</span>
        </div>
      )}

      {error && (
        <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
      )}

      {result && (
        <div className="space-y-3">
          <div>
            <label
              htmlFor={`reply-${review.id ?? 'x'}`}
              className="mb-1.5 flex items-center gap-1.5 text-sm font-medium text-slate-700"
            >
              <MessageCircle size={14} className="text-slate-500" />
              만든 답글 — 고쳐서 쓰셔도 됩니다
            </label>
            <textarea
              id={`reply-${review.id ?? 'x'}`}
              value={editedReply}
              onChange={(e) => setEditedReply(e.target.value)}
              rows={5}
              className="w-full resize-y rounded-lg border border-slate-200 p-3 text-sm
                         text-slate-800 outline-none focus:border-slate-400"
            />
          </div>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={copy}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm transition
                ${copied
                  ? 'bg-emerald-100 text-emerald-700'
                  : 'bg-slate-900 text-white hover:bg-slate-700'}`}
            >
              {copied ? <Check size={14} /> : <Copy size={14} />}
              {copied ? '복사했습니다' : '복사하기'}
            </button>
            <button
              type="button"
              onClick={generate}
              disabled={isGenerating}
              className="flex items-center gap-1.5 rounded-lg bg-slate-100 px-3 py-1.5
                         text-sm text-slate-700 transition hover:bg-slate-200
                         disabled:opacity-50"
            >
              <RefreshCw size={14} className={isGenerating ? 'animate-spin' : ''} />
              다시 만들기
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-sm text-slate-500 transition hover:text-slate-700"
            >
              닫기
            </button>
          </div>

          <p className="text-xs text-slate-400">
            복사하시면 이 답글을 쓰신 것으로 기록해 다음 답글이 더 사장님 말투에 가까워집니다.
          </p>
        </div>
      )}
    </div>
  );
}
