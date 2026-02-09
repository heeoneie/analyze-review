import { describe, it, expect, vi, beforeEach } from 'vitest';
import axios from 'axios';

vi.mock('axios', () => {
  const mockInstance = {
    get: vi.fn(() => Promise.resolve({ data: {} })),
    post: vi.fn(() => Promise.resolve({ data: {} })),
  };
  return {
    default: {
      create: vi.fn(() => mockInstance),
      __mockInstance: mockInstance,
    },
  };
});

// axios.create()가 호출된 후의 mock instance
const mockApi = axios.create();

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // 모듈 캐시 리셋 후 재임포트
  });

  it('uploadCSV sends FormData via POST', async () => {
    const { uploadCSV } = await import('../api/client.js');
    const file = new File(['test'], 'test.csv');
    await uploadCSV(file);
    expect(mockApi.post).toHaveBeenCalledWith('/data/upload', expect.any(FormData));
  });

  it('fetchSampleData calls GET /data/sample', async () => {
    const { fetchSampleData } = await import('../api/client.js');
    await fetchSampleData();
    expect(mockApi.get).toHaveBeenCalledWith('/data/sample');
  });

  it('runAnalysis calls POST /analysis/run', async () => {
    const { runAnalysis } = await import('../api/client.js');
    await runAnalysis();
    expect(mockApi.post).toHaveBeenCalledWith('/analysis/run');
  });

  it('getExperimentResults calls GET', async () => {
    const { getExperimentResults } = await import('../api/client.js');
    await getExperimentResults();
    expect(mockApi.get).toHaveBeenCalledWith('/analysis/experiment-results');
  });

  it('crawlReviews sends url and max_pages', async () => {
    const { crawlReviews } = await import('../api/client.js');
    await crawlReviews('https://coupang.com/products/123', 10);
    expect(mockApi.post).toHaveBeenCalledWith('/data/crawl', {
      url: 'https://coupang.com/products/123',
      max_pages: 10,
    });
  });

  it('crawlReviews uses default maxPages of 50', async () => {
    const { crawlReviews } = await import('../api/client.js');
    await crawlReviews('https://coupang.com/products/123');
    expect(mockApi.post).toHaveBeenCalledWith('/data/crawl', {
      url: 'https://coupang.com/products/123',
      max_pages: 50,
    });
  });

  it('getSettings calls GET /data/settings', async () => {
    const { getSettings } = await import('../api/client.js');
    await getSettings();
    expect(mockApi.get).toHaveBeenCalledWith('/data/settings');
  });

  it('updateSettings sends rating_threshold', async () => {
    const { updateSettings } = await import('../api/client.js');
    await updateSettings(2);
    expect(mockApi.post).toHaveBeenCalledWith('/data/settings', {
      rating_threshold: 2,
    });
  });

  it('getReviews passes page and page_size params', async () => {
    const { getReviews } = await import('../api/client.js');
    await getReviews(3, 50);
    expect(mockApi.get).toHaveBeenCalledWith('/data/reviews', {
      params: { page: 3, page_size: 50 },
    });
  });

  it('getReviews uses defaults page=1 pageSize=20', async () => {
    const { getReviews } = await import('../api/client.js');
    await getReviews();
    expect(mockApi.get).toHaveBeenCalledWith('/data/reviews', {
      params: { page: 1, page_size: 20 },
    });
  });
});
