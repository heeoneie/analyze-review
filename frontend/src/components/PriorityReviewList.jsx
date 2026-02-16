import { useState, useEffect, useCallback } from 'react';
import {
  AlertTriangle,
  Star,
  ChevronLeft,
  ChevronRight,
  Shield,
  Clock,
  FileText,
  Search,
} from 'lucide-react';
import { getPrioritizedReviews } from '../api/client';

const PAGE_SIZE = 10;

const LEVEL_CONFIG = {
  critical: { label: '긴급', color: 'bg-red-100 text-red-700 border-red-200', dot: 'bg-red-500' },
  high: { label: '높음', color: 'bg-orange-100 text-orange-700 border-orange-200', dot: 'bg-orange-500' },
  medium: { label: '보통', color: 'bg-yellow-100 text-yellow-700 border-yellow-200', dot: 'bg-yellow-500' },
  low: { label: '낮음', color: 'bg-gray-100 text-gray-600 border-gray-200', dot: 'bg-gray-400' },
};

const FILTER_OPTIONS = [
  { value: null, label: '전체' },
  { value: 'critical', label: '긴급' },
  { value: 'high', label: '높음' },
  { value: 'medium', label: '보통' },
  { value: 'low', label: '낮음' },
];

function PriorityBadge({ level }) {
  const config = LEVEL_CONFIG[level] || LEVEL_CONFIG.low;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${config.color}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${config.dot}`} />
      {config.label}
    </span>
  );
}

function ScoreBreakdown({ factors }) {
  const items = [
    { icon: Star, label: '별점', value: factors.rating, max: 40 },
    { icon: FileText, label: '상세도', value: factors.length, max: 20 },
    { icon: Search, label: '키워드', value: factors.keyword, max: 25 },
    { icon: Clock, label: '최신성', value: factors.recency, max: 15 },
  ];
  return (
    <div className="grid grid-cols-4 gap-2 mt-3 pt-3 border-t border-gray-100">
      {items.map(({ icon: Icon, label, value, max }) => (
        <div key={label} className="text-center">
          <Icon size={14} className="mx-auto text-gray-400 mb-1" />
          <div className="text-xs text-gray-500">{label}</div>
          <div className="text-xs font-medium text-gray-700">{value}/{max}</div>
        </div>
      ))}
    </div>
  );
}

export default function PriorityReviewList({ uploadInfo }) {
  const [reviews, setReviews] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filterLevel, setFilterLevel] = useState(null);
  const [expandedIdx, setExpandedIdx] = useState(null);

  const fetchReviews = useCallback(async (p, level) => {
    setIsLoading(true);
    setError(null);
    try {
      const { data } = await getPrioritizedReviews(p, PAGE_SIZE, level);
      setReviews(data.reviews);
      setTotalPages(data.total_pages);
      setTotal(data.total);
      setPage(p);
    } catch (err) {
      console.error('우선순위 리뷰 로딩 실패:', err);
      setError('리뷰를 불러오는 데 실패했습니다.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (uploadInfo) {
      fetchReviews(1, filterLevel);
    }
  }, [uploadInfo, fetchReviews, filterLevel]);

  const handleFilterChange = (level) => {
    setFilterLevel(level);
    setPage(1);
  };

  const renderStars = (rating) => (
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

  if (!uploadInfo) return null;

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Shield className="text-red-500" size={20} />
          <h2 className="text-lg font-semibold text-gray-900">대응 우선순위</h2>
          <span className="text-sm text-gray-500">부정 리뷰 {total}개</span>
        </div>
      </div>

      {/* 필터 버튼 */}
      <div className="flex gap-2 mb-4">
        {FILTER_OPTIONS.map(({ value, label }) => (
          <button
            key={label}
            onClick={() => handleFilterChange(value)}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
              filterLevel === value
                ? 'bg-gray-900 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {error && (
        <div className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2 mb-4">
          {error}
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-8 text-gray-500">로딩 중...</div>
      ) : reviews.length === 0 ? (
        <div className="text-center py-8 text-gray-400">해당 리뷰가 없습니다.</div>
      ) : (
        <>
          <div className="space-y-3">
            {reviews.map((review, idx) => {
              const priority = review.priority || {};
              const isExpanded = expandedIdx === idx;
              return (
                <div
                  key={`${page}-${idx}`}
                  className="border border-gray-100 rounded-xl p-4 hover:bg-gray-50 transition-colors cursor-pointer"
                  onClick={() => setExpandedIdx(isExpanded ? null : idx)}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      {renderStars(review.Ratings)}
                      <PriorityBadge level={priority.level} />
                      <span className="text-sm font-medium text-gray-700">
                        {priority.score}점
                      </span>
                    </div>
                    <span className="text-xs text-gray-400">
                      #{(page - 1) * PAGE_SIZE + idx + 1}
                    </span>
                  </div>
                  <p className={`text-sm text-gray-700 leading-relaxed ${isExpanded ? '' : 'line-clamp-3'}`}>
                    {review.Reviews}
                  </p>
                  {isExpanded && priority.factors && (
                    <ScoreBreakdown factors={priority.factors} />
                  )}
                </div>
              );
            })}
          </div>

          {/* 페이지네이션 */}
          <div className="flex items-center justify-center gap-4 mt-6 pt-4 border-t border-gray-100">
            <button
              onClick={() => fetchReviews(page - 1, filterLevel)}
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
              onClick={() => fetchReviews(page + 1, filterLevel)}
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
