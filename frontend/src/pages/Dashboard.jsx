import { useCallback, useEffect, useState } from 'react';
import {
  Link as LinkIcon,
  Loader2,
  MessageSquare,
  Star,
  AlertTriangle,
  Clock,
  ArrowLeft,
} from 'lucide-react';
import { collectReviews, getReviewSummary } from '../api/client';
import useAccessGate from '../hooks/useAccessGate';
import AccessGate from './AccessGate';
import LoginGate from './LoginGate';
import ReviewList from '../components/ReviewList';
import PriorityReviewList from '../components/PriorityReviewList';

const PLACEHOLDER = 'https://www.coupang.com/vp/products/...';

function formatWhen(iso) {
  if (!iso) return '아직 없음';
  const then = new Date(iso);
  const minutes = Math.floor((Date.now() - then.getTime()) / 60000);
  if (minutes < 1) return '방금';
  if (minutes < 60) return `${minutes}분 전`;
  if (minutes < 60 * 24) return `${Math.floor(minutes / 60)}시간 전`;
  return then.toLocaleDateString('ko-KR');
}

function SummaryCard({ icon: Icon, label, value, tone = 'text-slate-900' }) {
  return (
    <div className="rounded-2xl bg-white p-4 shadow-sm">
      <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
        <Icon size={14} />
        {label}
      </div>
      <div className={`mt-1 text-2xl font-bold ${tone}`}>{value}</div>
    </div>
  );
}

function CollectForm({ onCollected, onUnauthorized }) {
  const [url, setUrl] = useState('');
  const [isCollecting, setIsCollecting] = useState(false);
  const [error, setError] = useState(null);
  const [done, setDone] = useState(null);

  const isValidUrl = (() => {
    const trimmed = url.trim();
    if (!trimmed) return false;
    try {
      const parsed = new URL(trimmed);
      return parsed.protocol === 'http:' || parsed.protocol === 'https:';
    } catch {
      return false;
    }
  })();

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!isValidUrl || isCollecting) return;

    setIsCollecting(true);
    setError(null);
    setDone(null);
    try {
      const { data } = await collectReviews(url.trim());
      setDone(data);
      setUrl('');
      onCollected();
    } catch (err) {
      if (err.response?.status === 401) {
        onUnauthorized?.();
        return;
      }
      setError(
        err.response?.data?.detail
        || '리뷰를 가져오지 못했습니다. 주소를 확인하고 다시 시도해 주세요.',
      );
    } finally {
      setIsCollecting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="rounded-2xl bg-white p-5 shadow-sm">
      <label htmlFor="collect-url" className="mb-2 block text-sm font-semibold text-slate-700">
        상품 주소로 리뷰 모으기
      </label>
      <div className="flex flex-col gap-2 sm:flex-row">
        <div className="relative flex-1">
          <LinkIcon
            size={16}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
          />
          <input
            id="collect-url"
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder={PLACEHOLDER}
            disabled={isCollecting}
            className="w-full rounded-xl border border-slate-200 py-3 pl-9 pr-4 text-base
                       text-slate-900 outline-none placeholder:text-slate-400
                       focus:border-slate-400 disabled:bg-slate-50"
          />
        </div>
        <button
          type="submit"
          disabled={!isValidUrl || isCollecting}
          className="flex items-center justify-center gap-2 rounded-xl bg-slate-900 px-6 py-3
                     text-base font-semibold text-white transition hover:bg-slate-700
                     disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {isCollecting ? <Loader2 size={18} className="animate-spin" /> : null}
          {isCollecting ? '모으는 중' : '리뷰 모으기'}
        </button>
      </div>

      <p className="mt-2 text-xs text-slate-500">
        쿠팡 상품 페이지와 네이버 스마트스토어를 지원합니다. 리뷰가 많으면 30초쯤 걸립니다.
      </p>

      {done && (
        <p className="mt-3 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {done.saved > 0
            ? `${done.saved}개를 새로 담았습니다.`
            : '새로 담은 리뷰가 없습니다.'}
          {done.skipped > 0 && ` 이미 담아 둔 ${done.skipped}개는 넘어갔습니다.`}
        </p>
      )}

      {error && (
        <p className="mt-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
      )}
    </form>
  );
}

export default function Dashboard() {
  const { gate, open: openGate, lock: lockGate } = useAccessGate();
  // 수집이 끝나면 올린다. 아래 목록들이 이 값을 보고 다시 읽는다.
  const [refreshKey, setRefreshKey] = useState(0);
  const [summary, setSummary] = useState(null);

  const loadSummary = useCallback(async () => {
    try {
      const { data } = await getReviewSummary();
      setSummary(data);
    } catch (err) {
      if (err.response?.status === 401) lockGate();
      // 그 밖의 이유라면 요약만 접는다. 목록은 계속 보인다.
      setSummary(null);
    }
  }, [lockGate]);

  useEffect(() => {
    if (gate.status === 'open') loadSummary();
  }, [gate.status, refreshKey, loadSummary]);

  if (gate.status === 'checking') return <div className="min-h-screen bg-slate-50" />;
  if (gate.status === 'login') {
    return (
      <LoginGate authenticated={gate.authenticated} onClaimed={() => openGate(false)} />
    );
  }
  if (gate.status === 'locked') {
    return <AccessGate onUnlock={() => openGate(true)} />;
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-5 py-5">
          <div>
            <h1 className="text-xl font-bold text-slate-900">모아 둔 리뷰</h1>
            <p className="mt-1 text-sm text-slate-500">
              상품 주소를 넣으면 리뷰를 모아 두고, 먼저 답할 것부터 보여 드립니다.
            </p>
          </div>
          <a
            href="#/"
            className="flex shrink-0 items-center gap-1.5 rounded-xl border border-slate-200
                       px-3 py-2 text-sm font-medium text-slate-600 hover:border-slate-300"
          >
            <ArrowLeft size={15} />
            답글 만들기
          </a>
        </div>
      </header>

      <main className="mx-auto max-w-4xl space-y-5 px-5 py-6">
        <CollectForm
          onCollected={() => setRefreshKey((k) => k + 1)}
          onUnauthorized={lockGate}
        />

        {summary && summary.total > 0 && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <SummaryCard icon={MessageSquare} label="모은 리뷰" value={`${summary.total}개`} />
            <SummaryCard
              icon={AlertTriangle}
              label="부정 리뷰"
              value={`${summary.negative}개`}
              tone={summary.negative > 0 ? 'text-red-600' : 'text-slate-900'}
            />
            <SummaryCard icon={Star} label="평균 별점" value={summary.rating_average} />
            <SummaryCard
              icon={Clock}
              label="마지막 수집"
              value={formatWhen(summary.last_collected_at)}
            />
          </div>
        )}

        <PriorityReviewList refreshKey={refreshKey} onUnauthorized={lockGate} />
        <ReviewList refreshKey={refreshKey} onUnauthorized={lockGate} />
      </main>
    </div>
  );
}
