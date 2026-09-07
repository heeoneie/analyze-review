import { useState } from 'react';
import { Loader2, Plus, Sparkles, X } from 'lucide-react';
import { addStyleSamples } from '../api/client';

const RATINGS = [5, 4, 3, 2, 1];

// 이 별점 이상을 좋은 리뷰로 본다. 서버의 POSITIVE_RATING_THRESHOLD 와 같다.
const POSITIVE_FROM = 4;

// 처음에 몇 칸을 펼쳐 둘지. 빈 칸이 너무 많으면 숙제처럼 보이고, 하나만
// 있으면 여러 건을 넣어야 한다는 게 안 보인다.
const INITIAL_ROWS = 2;

const emptyRow = () => ({ review_text: '', rating: 5, reply: '' });

function SampleRow({ index, value, onChange, onRemove, canRemove }) {
  const set = (field) => (event) => onChange(index, field, event.target.value);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-sm font-semibold text-slate-700">{index + 1}번째</span>
        {canRemove && (
          <button
            type="button"
            onClick={() => onRemove(index)}
            aria-label={`${index + 1}번째 지우기`}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          >
            <X size={16} />
          </button>
        )}
      </div>

      <label className="mb-1 block text-xs font-medium text-slate-500">
        손님이 남긴 리뷰
      </label>
      <textarea
        rows={2}
        value={value.review_text}
        onChange={set('review_text')}
        placeholder="배달앱에서 리뷰를 복사해 붙여넣으세요"
        className="mb-3 w-full resize-y rounded-xl border border-slate-200 px-3 py-2 text-sm
                   text-slate-900 outline-none placeholder:text-slate-400 focus:border-slate-400"
      />

      <div className="mb-3 flex flex-wrap gap-1.5">
        {RATINGS.map((r) => (
          <button
            key={r}
            type="button"
            onClick={() => onChange(index, 'rating', r)}
            className={`rounded-lg border px-2.5 py-1 text-sm transition
              ${value.rating === r
                ? 'border-slate-900 bg-slate-900 text-white'
                : 'border-slate-200 bg-white text-slate-500 hover:border-slate-300'}`}
          >
            {'★'.repeat(r)}
          </button>
        ))}
      </div>

      <label className="mb-1 block text-xs font-medium text-slate-500">
        사장님이 직접 다신 답글
      </label>
      <textarea
        rows={2}
        value={value.reply}
        onChange={set('reply')}
        placeholder="그때 실제로 다셨던 답글을 그대로 적어 주세요"
        className="w-full resize-y rounded-xl border border-slate-200 px-3 py-2 text-sm
                   text-slate-900 outline-none placeholder:text-slate-400 focus:border-slate-400"
      />
    </div>
  );
}

export default function StyleOnboarding({ needed = 2, onDone, onSkip }) {
  const [rows, setRows] = useState(() =>
    Array.from({ length: INITIAL_ROWS }, emptyRow));
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);

  const filled = rows.filter((r) => r.review_text.trim() && r.reply.trim());
  // 기준은 성향별이다. 좋은 리뷰만 다섯 개 넣어도 아쉬운 리뷰 답글의
  // 말투는 배우지 못한다. 전체 개수로 안내하면 사장님이 다 됐다고 믿는다.
  const positives = filled.filter((r) => Number(r.rating) >= POSITIVE_FROM).length;
  const negatives = filled.length - positives;
  const missing = [
    positives < needed ? `좋은 리뷰 ${needed - positives}개` : null,
    negatives < needed ? `아쉬운 리뷰 ${needed - negatives}개` : null,
  ].filter(Boolean);

  const handleChange = (index, field, value) => {
    setRows((prev) => prev.map((row, i) => (
      i === index ? { ...row, [field]: value } : row
    )));
  };

  const handleRemove = (index) => {
    setRows((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!filled.length || isSaving) return;

    setIsSaving(true);
    setError(null);
    try {
      await addStyleSamples(filled.map((r) => ({
        review_text: r.review_text.trim(),
        rating: Number(r.rating),
        reply: r.reply.trim(),
      })));
      onDone();
    } catch (err) {
      setError(
        err.response?.data?.detail
        || '저장하지 못했습니다. 잠시 후 다시 시도해 주세요.',
      );
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-2xl px-5 py-5">
          <div className="flex items-center gap-2">
            <Sparkles size={18} className="text-slate-900" />
            <h1 className="text-xl font-bold text-slate-900">사장님 말투 알려주기</h1>
          </div>
          <p className="mt-1 text-sm text-slate-500">
            전에 직접 다셨던 답글을 몇 개만 보여 주시면, 앞으로 만드는 답글이
            사장님 말투를 따라갑니다.
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-5 py-6">
        <form onSubmit={handleSubmit} className="space-y-3">
          {rows.map((row, i) => (
            <SampleRow
              // 행을 지워도 남은 행의 입력이 섞이지 않도록 위치가 아닌
              // 값으로는 구분할 수 없다. 여기서는 재정렬이 없어 index 로 충분하다.
              key={i}  // eslint-disable-line react/no-array-index-key
              index={i}
              value={row}
              onChange={handleChange}
              onRemove={handleRemove}
              canRemove={rows.length > 1}
            />
          ))}

          <button
            type="button"
            onClick={() => setRows((prev) => [...prev, emptyRow()])}
            className="flex w-full items-center justify-center gap-1.5 rounded-xl border
                       border-dashed border-slate-300 py-3 text-sm font-medium text-slate-500
                       hover:border-slate-400 hover:text-slate-700"
          >
            <Plus size={16} />
            하나 더 넣기
          </button>

          <p className="pt-1 text-center text-sm text-slate-500">
            {missing.length === 0
              ? `${filled.length}개 담으셨습니다. 좋은 리뷰와 아쉬운 리뷰 모두 배울 수 있어요.`
              : `${missing.join(', ')}가 더 있으면 그 답글도 사장님 말투로 나옵니다.`}
          </p>

          {error && (
            <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
          )}

          <button
            type="submit"
            disabled={!filled.length || isSaving}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-slate-900
                       px-5 py-4 text-base font-semibold text-white transition
                       hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {isSaving ? <Loader2 size={18} className="animate-spin" /> : null}
            {isSaving ? '저장하는 중' : '저장하고 시작하기'}
          </button>

          <button
            type="button"
            onClick={onSkip}
            className="w-full py-2 text-sm text-slate-500 hover:text-slate-700"
          >
            나중에 할게요
          </button>
        </form>
      </main>
    </div>
  );
}
