import { useState, useEffect, useCallback } from 'react';
import { MessageSquare, Star, ChevronLeft, ChevronRight, Copy, Check } from 'lucide-react';
import { listReviews, finalizeStoreReply } from '../api/client';

function GeneratedReply({ review }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(review.reply);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      // 복사했다는 건 사장님이 이 답글을 쓰기로 했다는 뜻이다. 그때 말투
      // 학습의 재료가 된다. 기록에 실패해도 복사는 이미 됐다.
      if (review.sample_id) {
        finalizeStoreReply(review.sample_id, review.reply).catch(() => {});
      }
    } catch {
      // 클립보드를 막아 둔 브라우저도 있다. 답글은 화면에 그대로 보인다.
    }
  };

  return (
    <div className="mt-3 rounded-xl bg-slate-50 p-3">
      <div className="mb-1.5 flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-500">
          {review.reply_posted ? '게시한 답글' : '만들어 둔 답글'}
        </span>
        <button
          type="button"
          onClick={copy}
          className="flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium
                     text-slate-500 hover:bg-slate-200 hover:text-slate-700"
        >
          {copied ? <Check size={13} /> : <Copy size={13} />}
          {copied ? '복사함' : '복사'}
        </button>
      </div>
      <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
        {review.reply}
      </p>
    </div>
  );
}

export default function ReviewList({ refreshKey = 0, onUnauthorized }) {
  const [reviews, setReviews] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);

  const fetchReviews = useCallback(async (p) => {
    setIsLoading(true);
    try {
      const { data } = await listReviews(p, 10);
      setReviews(data.reviews);
      setTotalPages(data.total_pages);
      setTotal(data.total);
      setPage(p);
    } catch (err) {
      // 401 이면 화면에 오류만 띄우고 끝내면 안 된다. 사장님이 다시
      // 들어올 길이 없어진다. 게이트를 되돌려 로그인·코드 화면을 띄운다.
      if (err.response?.status === 401) onUnauthorized?.();
      else console.error('리뷰 로딩 실패:', err);
    } finally {
      setIsLoading(false);
    }
  }, [onUnauthorized]);

  // 화면에 들어오면 바로 읽는다. 리뷰는 DB 에 있으므로 업로드나 수집을
  // 기다릴 필요가 없다. 수집이 끝나면 refreshKey 가 바뀌어 다시 읽는다.
  useEffect(() => {
    fetchReviews(1);
  }, [refreshKey, fetchReviews]);

  const renderStars = (rating) => {
    return (
      <div className="flex gap-0.5">
        {[1, 2, 3, 4, 5].map((star) => (
          <Star
            key={star}
            size={14}
            className={star <= rating ? 'text-yellow-400 fill-yellow-400' : 'text-gray-300'}
          />
        ))}
      </div>
    );
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
      <div className="flex items-center gap-2 mb-4">
        <MessageSquare className="text-blue-500" size={20} />
        <h2 className="text-lg font-semibold text-gray-900">수집된 리뷰</h2>
        <span className="text-sm text-gray-500">총 {total}개</span>
      </div>

      {isLoading ? (
        <div className="text-center py-8 text-gray-500">로딩 중...</div>
      ) : (
        <>
          <div className="space-y-3">
            {reviews.map((review, idx) => (
              <div
                key={idx}
                className="border border-gray-100 rounded-xl p-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center justify-between mb-2">
                  {renderStars(review.Ratings)}
                  <span className="text-xs text-gray-400">#{(page - 1) * 10 + idx + 1}</span>
                </div>
                <p className="text-sm text-gray-700 leading-relaxed line-clamp-3">
                  {review.Reviews}
                </p>
                {review.reply && <GeneratedReply review={review} />}
              </div>
            ))}
          </div>

          {/* 페이지네이션 */}
          <div className="flex items-center justify-center gap-4 mt-6 pt-4 border-t border-gray-100">
            <button
              onClick={() => fetchReviews(page - 1)}
              disabled={page <= 1}
              className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ChevronLeft size={16} />
              이전
            </button>
            <span className="text-sm text-gray-600">
              {page} / {totalPages}
            </span>
            <button
              onClick={() => fetchReviews(page + 1)}
              disabled={page >= totalPages}
              className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed"
            >
              다음
              <ChevronRight size={16} />
            </button>
          </div>
        </>
      )}
    </div>
  );
}
