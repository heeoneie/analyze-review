import { useEffect, useRef, useState } from 'react';
import { Copy, Check, RefreshCw, Loader2, ListChecks } from 'lucide-react';
import {
  clearAccessCode,
  generateStoreReply,
  finalizeStoreReply,
} from '../api/client';
import useAccessGate from '../hooks/useAccessGate';
import AccessGate from './AccessGate';
import LoginGate from './LoginGate';

const RATINGS = [5, 4, 3, 2, 1];

const MENU_PLACEHOLDER = '해물짬뽕 | 도야짜장면 | 군만두3P';

function StarPicker({ value, onChange }) {
  return (
    <div className="flex gap-2">
      {RATINGS.map((n) => {
        const active = value === n;
        return (
          <button
            key={n}
            type="button"
            onClick={() => onChange(n)}
            aria-pressed={active}
            className={`flex-1 rounded-xl border py-3 text-base font-semibold transition
              ${active
                ? 'border-amber-400 bg-amber-50 text-amber-700'
                : 'border-slate-200 bg-white text-slate-500 hover:border-slate-300'}`}
          >
            <span aria-hidden="true">{'★'.repeat(n)}</span>
            <span className="sr-only">{n}점</span>
          </button>
        );
      })}
    </div>
  );
}

function CopyButton({ text, sampleId }) {
  const [copied, setCopied] = useState(false);
  const timer = useRef(null);

  useEffect(() => () => clearTimeout(timer.current), []);

  const copy = async () => {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        // 구형 모바일 브라우저 대비
        const area = document.createElement('textarea');
        area.value = text;
        area.style.position = 'fixed';
        area.style.opacity = '0';
        document.body.appendChild(area);
        area.select();
        document.execCommand('copy');
        document.body.removeChild(area);
      }
      setCopied(true);
      timer.current = setTimeout(() => setCopied(false), 2000);

      // 복사했다는 건 사장님이 이 답글을 쓰기로 했다는 뜻이다. 그 시점의
      // 문장을 그대로 남긴다 — 고쳐 썼다면 고친 채로 저장된다.
      // 기록에 실패해도 복사는 이미 됐으므로 화면에는 영향을 주지 않는다.
      if (sampleId) {
        finalizeStoreReply(sampleId, text).catch(() => {});
      }
    } catch {
      setCopied(false);
    }
  };

  return (
    <button
      type="button"
      onClick={copy}
      className={`flex w-full items-center justify-center gap-2 rounded-xl px-5 py-3 text-base font-semibold transition
        ${copied ? 'bg-emerald-600 text-white' : 'bg-slate-900 text-white hover:bg-slate-700'}`}
    >
      {copied ? <Check size={18} /> : <Copy size={18} />}
      {copied ? '복사했습니다' : '복사하기'}
    </button>
  );
}

export default function ReplyStudio() {
  const { gate, open: openGate, lock: lockGate } = useAccessGate();
  const [reviewText, setReviewText] = useState('');
  const [rating, setRating] = useState(5);
  const [menu, setMenu] = useState('');
  const [result, setResult] = useState(null);
  // 생성본과 별개로 둔다. 사장님이 고친 문장이 복사·기록 대상이다.
  const [editedReply, setEditedReply] = useState('');
  const [drafts, setDrafts] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);


  const canSubmit = (reviewText.trim() || menu.trim()) && !isLoading;

  const run = async (previous) => {
    setError(null);
    setIsLoading(true);
    try {
      // 다시 생성할 때는 앞서 나온 문장과 겹치지 않도록 되돌려 보낸다.
      const history = previous ? [previous, ...drafts] : [];
      const { data } = await generateStoreReply({
        review_text: reviewText,
        rating,
        menu,
        avoid_openings: history.map((d) => d.opening_sentence).filter(Boolean),
        avoid_closings: history.map((d) => d.closing_sentence).filter(Boolean),
        exclude_angles: history.map((d) => d.opening_angle).filter(Boolean),
        exclude_closings: history.map((d) => d.closing_move).filter(Boolean),
      });
      if (previous) setDrafts((prev) => [previous, ...prev].slice(0, 5));
      setResult(data);
      setEditedReply(data.reply || '');
    } catch (err) {
      if (err.response?.status === 401) {
        clearAccessCode();
        lockGate();
        return;
      }
      setError(err.response?.data?.detail || '답변을 만들지 못했습니다. 잠시 후 다시 시도해 주세요.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!canSubmit) return;
    setDrafts([]);
    run(null);
  };

  if (gate.status === 'checking') return <div className="min-h-screen bg-slate-50" />;
  if (gate.status === 'login') {
    return (
      <LoginGate
        authenticated={gate.authenticated}
        onClaimed={() => openGate(false)}
      />
    );
  }
  if (gate.status === 'locked') {
    return <AccessGate onUnlock={() => openGate(true)} />;
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-2xl items-start justify-between gap-4 px-5 py-5">
          <div>
            <h1 className="text-xl font-bold text-slate-900">리뷰 답글 만들기</h1>
            <p className="mt-1 text-sm text-slate-500">
              리뷰를 붙여넣고 별점과 시킨 메뉴를 넣으면, 그 주문에 맞는 답글을 만들어 드립니다.
            </p>
          </div>
          <a
            href="#dashboard"
            className="flex shrink-0 items-center gap-1.5 rounded-xl border border-slate-200
                       px-3 py-2 text-sm font-medium text-slate-600 hover:border-slate-300"
          >
            <ListChecks size={15} />
            모아 둔 리뷰
          </a>
        </div>
      </header>

      <main className="mx-auto max-w-2xl space-y-5 px-5 py-6">
        <form onSubmit={handleSubmit} className="space-y-5 rounded-2xl bg-white p-5 shadow-sm">
          <div>
            <label htmlFor="review" className="mb-2 block text-sm font-semibold text-slate-700">
              리뷰 내용
            </label>
            <textarea
              id="review"
              rows={4}
              value={reviewText}
              onChange={(e) => setReviewText(e.target.value)}
              placeholder="배달앱에서 리뷰를 복사해 붙여넣으세요. 별점만 남긴 리뷰면 비워 두셔도 됩니다."
              className="w-full resize-y rounded-xl border border-slate-200 px-4 py-3 text-base
                         text-slate-900 outline-none placeholder:text-slate-400 focus:border-slate-400"
            />
          </div>

          <div>
            <span className="mb-2 block text-sm font-semibold text-slate-700">별점</span>
            <StarPicker value={rating} onChange={setRating} />
          </div>

          <div>
            <label htmlFor="menu" className="mb-2 block text-sm font-semibold text-slate-700">
              주문 메뉴 <span className="font-normal text-slate-400">(선택)</span>
            </label>
            <input
              id="menu"
              value={menu}
              onChange={(e) => setMenu(e.target.value)}
              placeholder={MENU_PLACEHOLDER}
              className="w-full rounded-xl border border-slate-200 px-4 py-3 text-base
                         text-slate-900 outline-none placeholder:text-slate-400 focus:border-slate-400"
            />
            <p className="mt-2 text-xs text-slate-500">
              메뉴를 넣으면 그 메뉴 이야기가 답글에 들어갑니다. 여러 개는 <code>|</code> 로 구분하세요.
            </p>
          </div>

          <button
            type="submit"
            disabled={!canSubmit}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-slate-900 px-5 py-4
                       text-base font-semibold text-white transition hover:bg-slate-700
                       disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {isLoading ? <Loader2 size={18} className="animate-spin" /> : null}
            {isLoading ? '만드는 중…' : '답글 만들기'}
          </button>
        </form>

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {result && (
          <section className="space-y-4 rounded-2xl bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-700">만들어진 답글</h2>
              <span className="text-xs text-slate-400">{editedReply.length}자</span>
            </div>

            {/* 그대로 써도 되고 고쳐 써도 된다. 고친 답글은 다음 답글이
                사장님 말투에 가까워지는 재료가 된다. */}
            <textarea
              value={editedReply}
              onChange={(e) => setEditedReply(e.target.value)}
              rows={6}
              className="w-full resize-y whitespace-pre-wrap rounded-xl bg-slate-50 px-4 py-4
                         text-base leading-relaxed text-slate-900 outline-none
                         focus:bg-white focus:ring-1 focus:ring-slate-300"
            />

            <div className="flex flex-col gap-2 sm:flex-row">
              <div className="sm:flex-1">
                <CopyButton text={editedReply} sampleId={result.sample_id} />
              </div>
              <button
                type="button"
                onClick={() => run(result)}
                disabled={isLoading}
                className="flex items-center justify-center gap-2 rounded-xl border border-slate-200
                           px-5 py-3 text-base font-semibold text-slate-700 transition
                           hover:border-slate-300 disabled:cursor-not-allowed disabled:text-slate-400"
              >
                <RefreshCw size={18} className={isLoading ? 'animate-spin' : ''} />
                다시 만들기
              </button>
            </div>

            {result.violations?.length > 0 && (
              <p className="text-xs text-amber-700">
                걸러내지 못한 부분이 있습니다: {result.violations.join(' · ')}
              </p>
            )}
          </section>
        )}

        {drafts.length > 0 && (
          <section className="space-y-3 rounded-2xl bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-700">앞서 만든 답글</h2>
            {drafts.map((draft) => (
              <div
                key={draft.reply}
                className="space-y-2 border-t border-slate-100 pt-3 first:border-0 first:pt-0"
              >
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-500">
                  {draft.reply}
                </p>
                <CopyButton text={draft.reply} />
              </div>
            ))}
          </section>
        )}
      </main>
    </div>
  );
}
