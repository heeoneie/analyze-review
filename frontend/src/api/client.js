import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  timeout: 180000, // 크롤링 시간 고려하여 3분
});

export const uploadCSV = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/data/upload', formData);
};

export const fetchSampleData = () => api.get('/data/sample');
export const runAnalysis = () => api.post('/analysis/run');
export const getExperimentResults = () => api.get('/analysis/experiment-results');

// 크롤링 API
export const crawlReviews = (url, maxPages = 50) =>
  api.post('/data/crawl', { url, max_pages: maxPages });

// 설정 API
export const getSettings = () => api.get('/data/settings');
export const updateSettings = (ratingThreshold) =>
  api.post('/data/settings', { rating_threshold: ratingThreshold });

// 리뷰 목록 API
export const getReviews = (page = 1, pageSize = 20) =>
  api.get('/data/reviews', { params: { page, page_size: pageSize } });

// 우선순위 리뷰 API
export const getPrioritizedReviews = (page = 1, pageSize = 20, level = null) =>
  api.get('/data/reviews/prioritized', {
    params: { page, page_size: pageSize, ...(level && { level }) },
  });

// 답변 생성 API
export const generateReply = (reviewText, rating, category = null) =>
  api.post('/reply/generate', { review_text: reviewText, rating, category });

export const generateBatchReplies = (reviews) =>
  api.post('/reply/generate-batch', { reviews });

// 답변 가이드 API
export const getReplyGuide = (category) =>
  api.post('/reply/guide', { category });

export const getAllGuides = () => api.get('/reply/guides');

// 리스크 인텔리전스 API
export const generateOntology = (analysisData) => api.post('/risk/ontology', analysisData);
export const generateComplianceReport = (analysisData) => api.post('/risk/compliance', analysisData);
export const generateMeetingAgenda = (analysisData) => api.post('/risk/meeting', analysisData);
