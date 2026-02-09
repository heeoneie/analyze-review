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
