import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import ModelQuality from '../components/ModelQuality';
import { getEvaluationMetrics, getDatasetInfo } from '../api/client';

vi.mock('../api/client', () => ({
  getEvaluationMetrics: vi.fn(),
  getDatasetInfo: vi.fn(),
}));

vi.mock('../contexts/LangContext', () => ({
  useLang: () => ({ lang: 'ko' }),
}));

beforeEach(() => {
  vi.clearAllMocks();
  getDatasetInfo.mockResolvedValue({ data: { total_samples: 0, label_distribution: {} } });
});

describe('ModelQuality — 측정 전 상태', () => {
  it('측정 전이면 카드를 지우지 않고 "측정 전" 으로 표시한다', async () => {
    // 카드를 통째로 안 그리면 "아직 측정 안 함" 과 "API 가 죽음" 이
    // 화면에서 구분되지 않는다.
    getEvaluationMetrics.mockResolvedValue({
      data: {
        status: 'not_measured',
        measured: false,
        reason: '사람이 직접 라벨링한 평가 표본이 아직 없습니다.',
        detail: '순환 논리가 되어 숫자가 무의미합니다.',
      },
    });

    render(<ModelQuality />);

    await waitFor(() => {
      expect(screen.getByText('측정 전')).toBeInTheDocument();
    });
    expect(screen.getByText(/평가 표본이 아직 없습니다/)).toBeInTheDocument();
  });

  it('측정 전에는 어떤 퍼센트 수치도 렌더링하지 않는다', async () => {
    getEvaluationMetrics.mockResolvedValue({
      data: { status: 'not_measured', measured: false, reason: '표본 없음' },
    });

    const { container } = render(<ModelQuality />);
    await waitFor(() => expect(screen.getByText('측정 전')).toBeInTheDocument());

    expect(container.textContent).not.toMatch(/\d+\.\d%/);
    expect(screen.queryByText('Accuracy')).not.toBeInTheDocument();
  });

  it('overall 이 비어 있으면 측정값이 있다고 주장하지 않는다', async () => {
    getEvaluationMetrics.mockResolvedValue({
      data: { status: 'measured', measured: true },
    });

    render(<ModelQuality />);
    await waitFor(() => expect(screen.getByText('측정 전')).toBeInTheDocument());
  });

  it('출처가 확인된 측정값은 정상 렌더링한다', async () => {
    getEvaluationMetrics.mockResolvedValue({
      data: {
        status: 'measured',
        measured: true,
        meta: { model: 'gpt-4o-mini', ground_truth: 'human' },
        overall: {
          accuracy: 0.723,
          precision_weighted: 0.701,
          recall_weighted: 0.744,
          f1_weighted: 0.715,
        },
        per_class: {},
      },
    });

    render(<ModelQuality />);
    await waitFor(() => expect(screen.getByText('Accuracy')).toBeInTheDocument());
    expect(screen.getByText('72.3%')).toBeInTheDocument();
    expect(screen.queryByText('측정 전')).not.toBeInTheDocument();
  });
});
