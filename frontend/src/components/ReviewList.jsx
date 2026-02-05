import { useState, useEffect } from 'react';
import { MessageSquare, Star, ChevronLeft, ChevronRight } from 'lucide-react';
import { getReviews } from '../api/client';

export default function ReviewList({ uploadInfo }) {
  const [reviews, setReviews] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);

  const fetchReviews = async (p) => {
    setIsLoading(true);
    try {
      const { data } = await getReviews(p, 10);
      setReviews(data.reviews);
      setTotalPages(data.total_pages);
      setTotal(data.total);
      setPage(p);
    } catch (err) {
      console.error('리뷰 로딩 실패:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (uploadInfo) {
      fetchReviews(1);
    }
  }, [uploadInfo]);

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

  if (!uploadInfo) return null;

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
