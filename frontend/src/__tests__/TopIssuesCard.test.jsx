import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import TopIssuesCard from '../components/TopIssuesCard';

describe('TopIssuesCard', () => {
  it('renders null when topIssues is empty', () => {
    const { container } = render(<TopIssuesCard topIssues={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders null when topIssues is null', () => {
    const { container } = render(<TopIssuesCard topIssues={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders issues with rank badges', () => {
    const issues = [
      { category: 'delivery_delay', count: 10, percentage: 40, examples: ['Late delivery'] },
      { category: 'poor_quality', count: 5, percentage: 20, examples: ['Bad quality'] },
    ];
    render(<TopIssuesCard topIssues={issues} />);
    expect(screen.getByText('배송 지연')).toBeInTheDocument();
    expect(screen.getByText('품질 불량')).toBeInTheDocument();
    expect(screen.getByText('1위')).toBeInTheDocument();
    expect(screen.getByText('2위')).toBeInTheDocument();
  });

  it('displays example text in quotes', () => {
    const issues = [
      { category: 'delivery_delay', count: 3, percentage: 30, examples: ['Package was late'] },
    ];
    render(<TopIssuesCard topIssues={issues} />);
    expect(screen.getByText(/"Package was late"/)).toBeInTheDocument();
  });
});
