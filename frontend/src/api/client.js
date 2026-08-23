import axios from 'axios';

// 배포 시에는 백엔드가 빌드된 프론트엔드를 같이 서빙하므로 같은 출처를 쓴다.
const defaultBaseURL = import.meta.env.DEV ? 'http://localhost:8000/api' : '/api';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || defaultBaseURL,
  timeout: 180000, // 크롤링 시간 고려하여 3분
});

// 사장님용 단독 화면의 접속 코드. 이 브라우저에만 저장한다.
// 계정도 서버 세션도 두지 않는다.
const ACCESS_CODE_KEY = 'reply_access_code';

export const getAccessCode = () => localStorage.getItem(ACCESS_CODE_KEY) || '';
export const setAccessCode = (code) => localStorage.setItem(ACCESS_CODE_KEY, code);
export const clearAccessCode = () => localStorage.removeItem(ACCESS_CODE_KEY);

const withAccessCode = (code) => ({ headers: { 'X-Access-Code': code ?? getAccessCode() } });

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
  api.post(
    '/reply/generate',
    { review_text: reviewText, rating, category },
    withAccessCode(),
  );

export const generateBatchReplies = (reviews) =>
  api.post('/reply/generate-batch', { reviews }, withAccessCode());

// 답변 가이드 API
export const getReplyGuide = (category) =>
  api.post('/reply/guide', { category });

export const getAllGuides = () => api.get('/reply/guides');

// 리스크 인텔리전스 API
export const generateOntology = (analysisData) => api.post('/risk/ontology', analysisData);
export const generateComplianceReport = (analysisData) => api.post('/risk/compliance', analysisData);
export const generateMeetingAgenda = (analysisData) => api.post('/risk/meeting', analysisData);
export const runDemoScenario = (industry = 'ecommerce', lang = 'ko') =>
  api.post('/risk/demo', null, { params: { industry, lang } });

// 플레이북 API
export const generatePlaybook = (body, config = {}) =>
  api.post('/risk/playbook/generate', body, config);

// KPI & Amazon pipeline
export const getKpiSummary = () => api.get('/kpi/summary');
export const getRiskTimeline = (limit = 20) =>
  api.get('/kpi/timeline', { params: { limit } });
export const ingestAmazon = (url) => api.post('/data/amazon', { url });

// AI 모델 평가 API
export const getEvaluationMetrics = () => api.get('/evaluate/metrics');
export const getDatasetInfo = () => api.get('/evaluate/dataset/info');

// YouTube 실데이터 분석 API
export const analyzeYouTube = (query, brand, options = {}) =>
  api.post('/youtube/analyze', {
    query,
    brand,
    industry: options.industry || 'ecommerce',
    lang: options.lang || 'ko',
    max_videos: options.maxVideos || 3,
    max_comments_per_video: options.maxComments || 15,
  });
// 사장님용 단독 답글 화면 API
export const getReplyConfig = () => api.get('/reply/config');
export const verifyAccessCode = (code) =>
  api.post('/reply/verify', {}, withAccessCode(code));
export const generateStoreReply = (payload) =>
  api.post('/reply/store/generate', payload, withAccessCode());
