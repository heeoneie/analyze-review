import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import PriorityReviewList from '../components/PriorityReviewList';
import { listPrioritizedReviews, generateStoreReply } from '../api/client';

vi.mock('../api/client', () => ({
  listPrioritizedReviews: vi.fn(),
  generateStoreReply: vi.fn(),
  finalizeStoreReply: vi.fn(),
}));

const makeReview = (text, overrides = {}) => ({
  Ratings: 1,
  Reviews: text,
  priority: {
    score: 85,
    level: 'critical',
    factors: { rating: 40, length: 20, keyword: 25, recency: 0 },
  },
  ...overrides,
});

const pageOf = (reviews, totalPages = 2) => ({
  data: {
    reviews,
    total: reviews.length,
    page: 1,
    page_size: 10,
    total_pages: totalPages,
  },
});

describe('PriorityReviewList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // 예전에는 업로드 전이면 아무것도 그리지 않았다. 이제 리뷰가 DB 에 있어
  // 화면에 들어오는 즉시 읽는다. 빈 매장이면 빈 목록을 보여 준다.
  it('fetches on mount without waiting for an upload', async () => {
    listPrioritizedReviews.mockResolvedValue(pageOf([], 0));

    render(<PriorityReviewList />);

    await waitFor(() => expect(listPrioritizedReviews).toHaveBeenCalled());
  });

  // 이슈 #35: 페이지를 넘기면 펼침/답변 상태가 따라오면 안 된다
  it('resets expanded and reply state when the page changes', async () => {
    listPrioritizedReviews
      .mockResolvedValueOnce(pageOf([makeReview('첫 페이지 리뷰입니다')]))
      .mockResolvedValueOnce(pageOf([makeReview('두 번째 페이지 리뷰입니다')]));
    generateStoreReply.mockResolvedValue({
      data: {
        reply: '첫 페이지 리뷰에 대한 답변',
        sample_id: 1,
      },
    });

    render(<PriorityReviewList />);
    fireEvent.click(await screen.findByText('첫 페이지 리뷰입니다'));
    fireEvent.click(screen.getByText('답변 작성하기 →'));
    fireEvent.click(screen.getByText('사장님 말투로 답글 만들기'));
    await screen.findByDisplayValue('첫 페이지 리뷰에 대한 답변');

    fireEvent.click(screen.getByRole('button', { name: /다음/ }));
    await screen.findByText('두 번째 페이지 리뷰입니다');

    // 이전 페이지의 답변이 엉뚱한 리뷰에 남아 있으면 안 된다
    expect(screen.queryByDisplayValue('첫 페이지 리뷰에 대한 답변')).toBeNull();
    // 행도 접혀 있어야 한다 (펼쳤을 때만 점수 상세가 보인다)
    expect(screen.queryByText('상세도')).toBeNull();
    expect(screen.queryByText('답변 작성하기 →')).toBeNull();
  });

  // 이슈 #35: 필터를 바꿔도 같은 문제가 생기면 안 된다
  it('resets expanded and reply state when the filter changes', async () => {
    listPrioritizedReviews
      .mockResolvedValueOnce(pageOf([makeReview('전체 목록 리뷰')], 1))
      .mockResolvedValueOnce(pageOf([makeReview('긴급 목록 리뷰')], 1));

    render(<PriorityReviewList />);
    fireEvent.click(await screen.findByText('전체 목록 리뷰'));
    expect(screen.getByText('답변 작성하기 →')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '긴급' }));
    await screen.findByText('긴급 목록 리뷰');

    expect(screen.queryByText('답변 작성하기 →')).toBeNull();
  });

  it('renders stars from a string rating', async () => {
    listPrioritizedReviews.mockResolvedValue(
      pageOf([makeReview('문자열 별점 리뷰', { Ratings: '1.0' })], 1),
    );

    const { container } = render(<PriorityReviewList />);
    await screen.findByText('문자열 별점 리뷰');
    await waitFor(() => {
      expect(container.querySelectorAll('.fill-yellow-400')).toHaveLength(1);
    });
  });
});
