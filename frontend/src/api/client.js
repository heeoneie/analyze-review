import axios from 'axios';

// 배포 시에는 백엔드가 빌드된 프론트엔드를 같이 서빙하므로 같은 출처를 쓴다.
const defaultBaseURL = import.meta.env.DEV ? 'http://localhost:8000/api' : '/api';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || defaultBaseURL,
  timeout: 180000, // 크롤링 시간 고려하여 3분
  // 세션 쿠키. 배포는 동일 출처라 없어도 되지만, vite dev 서버(5173)에서
  // 백엔드(8000)를 부를 때는 이게 없으면 로그인이 유지되지 않는다.
  withCredentials: true,
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

export const runAnalysis = () => api.post('/analysis/run');

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

// 사장님용 단독 답글 화면 API
export const getReplyConfig = () => api.get('/reply/config');
export const verifyAccessCode = (code) =>
  api.post('/reply/verify', {}, withAccessCode(code));
export const generateStoreReply = (payload) =>
  api.post('/reply/store/generate', payload, withAccessCode());

// 계정 API
export const getAuthConfig = () => api.get('/auth/config');
export const getMe = () => api.get('/auth/me');
export const logout = () => api.post('/auth/logout');
export const claimStore = (accessCode) =>
  api.post('/auth/claim-store', { access_code: accessCode });

// 수집한 리뷰 (DB 저장, 매장별로 갈림)
export const collectReviews = (url, maxPages = 10) =>
  api.post('/reviews/collect', { url, max_pages: maxPages }, withAccessCode());

export const listReviews = (page = 1, pageSize = 10) =>
  api.get('/reviews', { params: { page, page_size: pageSize }, ...withAccessCode() });

export const listPrioritizedReviews = (page = 1, pageSize = 10, level = null) =>
  api.get('/reviews/prioritized', {
    params: { page, page_size: pageSize, ...(level ? { level } : {}) },
    ...withAccessCode(),
  });

export const getReviewSummary = () =>
  api.get('/reviews/summary', withAccessCode());

// 사장님이 실제로 게시한 답글을 기록한다. 말투 학습은 이 기록만 쓴다.
export const finalizeStoreReply = (sampleId, finalReply) =>
  api.post('/reply/store/finalize', { sample_id: sampleId, final_reply: finalReply },
    withAccessCode());
