import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ActionPlan from '../components/ActionPlan';

describe('ActionPlan', () => {
  it('renders null when recommendations is empty', () => {
    const { container } = render(<ActionPlan recommendations={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders null when recommendations is null', () => {
    const { container } = render(<ActionPlan recommendations={null} />);
    expect(container.firstChild).toBeNull();
  });

  // 백엔드(analyzer.py)가 실제로 돌려주는 형태. 예전에는 문자열이었다.
  it('renders structured recommendation objects', () => {
    const recs = [
      {
        title: '배송 포장 개선',
        problem: '파손 관련 리뷰 12건',
        action: '완충재를 3겹으로 변경, 물류팀 담당',
        expected_impact: '파손 문의 40% 감소',
      },
    ];
    render(<ActionPlan recommendations={recs} />);
    expect(screen.getByText('배송 포장 개선')).toBeInTheDocument();
    expect(screen.getByText(/파손 관련 리뷰 12건/)).toBeInTheDocument();
    expect(screen.getByText(/완충재를 3겹으로 변경/)).toBeInTheDocument();
    expect(screen.getByText(/파손 문의 40% 감소/)).toBeInTheDocument();
  });

  it('tolerates missing optional fields', () => {
    render(<ActionPlan recommendations={[{ title: '제목만 있는 액션' }]} />);
    expect(screen.getByText('제목만 있는 액션')).toBeInTheDocument();
  });

  it('renders all recommendations with numbered badges', () => {
    const recs = ['첫 번째 액션', '두 번째 액션', '세 번째 액션'];
    render(<ActionPlan recommendations={recs} />);
    expect(screen.getByText('첫 번째 액션')).toBeInTheDocument();
    expect(screen.getByText('두 번째 액션')).toBeInTheDocument();
    expect(screen.getByText('세 번째 액션')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });
});
