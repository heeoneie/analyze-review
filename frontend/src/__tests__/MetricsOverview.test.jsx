import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import MetricsOverview from '../components/MetricsOverview';

describe('MetricsOverview', () => {
  it('renders all 4 metric cards', () => {
    const stats = { total_reviews: 100, negative_reviews: 30, negative_ratio: 30.0 };
    render(<MetricsOverview stats={stats} categoryCount={5} />);
    expect(screen.getByText('100')).toBeInTheDocument();
    expect(screen.getByText('30')).toBeInTheDocument();
    expect(screen.getByText('30%')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('renders 0 values when stats is null', () => {
    render(<MetricsOverview stats={null} categoryCount={null} />);
    const zeros = screen.getAllByText('0');
    expect(zeros.length).toBeGreaterThanOrEqual(3);
  });

  it('renders labels in Korean', () => {
    render(<MetricsOverview stats={{}} categoryCount={0} />);
    expect(screen.getByText('총 리뷰 수')).toBeInTheDocument();
    expect(screen.getByText('부정 리뷰 수')).toBeInTheDocument();
    expect(screen.getByText('부정 비율')).toBeInTheDocument();
    expect(screen.getByText('발견된 카테고리')).toBeInTheDocument();
  });
});
