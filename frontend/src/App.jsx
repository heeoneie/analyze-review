import { useState } from 'react';
import {
  uploadCSV,
  fetchSampleData,
  runAnalysis,
  crawlReviews,
  updateSettings,
} from './api/client';
import FileUpload from './components/FileUpload';
import ReviewList from './components/ReviewList';
import LoadingSpinner from './components/LoadingSpinner';
import MetricsOverview from './components/MetricsOverview';
import CategoryChart from './components/CategoryChart';
import TopIssuesCard from './components/TopIssuesCard';
import EmergingIssues from './components/EmergingIssues';
import ActionPlan from './components/ActionPlan';
import PriorityReviewList from './components/PriorityReviewList';
import ReplyGuide from './components/ReplyGuide';
import RiskIntelligence from './components/RiskIntelligence';
import './index.css';

const TABS = [
  { id: 'analysis', label: '분석 대시보드' },
  { id: 'reply', label: '리뷰 답변' },
  { id: 'risk', label: '리스크 인텔리전스' },
];

function App() {
  const [uploadInfo, setUploadInfo] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [ratingThreshold, setRatingThreshold] = useState(3);
  const [activeTab, setActiveTab] = useState('analysis');

  const executeWithAnalysis = async (apiCall, errorMsg) => {
    try {
      setError(null);
      setIsLoading(true);
      const { data } = await apiCall();
      setUploadInfo(data);
      const result = await runAnalysis();
      setAnalysisResult(result.data);
    } catch (err) {
      setError(err.response?.data?.detail || errorMsg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRatingThresholdChange = async (value) => {
    setRatingThreshold(value);
    try {
      await updateSettings(value);
      const result = await runAnalysis();
      setAnalysisResult(result.data);
    } catch (err) {
      console.error('설정 업데이트 실패:', err);
    }
  };

  const handleUpload = (file) =>
    executeWithAnalysis(() => uploadCSV(file), '분석 중 오류가 발생했습니다.');

  const handleUseSample = () =>
    executeWithAnalysis(() => fetchSampleData(), '분석 중 오류가 발생했습니다.');

  const handleCrawl = (url) =>
    executeWithAnalysis(() => crawlReviews(url), '크롤링 중 오류가 발생했습니다.');

  const categories = analysisResult?.all_categories ?? {};

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <h1 className="text-xl font-bold text-gray-900">
            RepShield — AI Reputation Insurance
          </h1>
          <p className="text-sm text-gray-500">멀티채널 리스크 모니터링 · 온톨로지 분석 · 컴플라이언스 자동화</p>

          {/* 탭 네비게이션 */}
          {analysisResult && !isLoading && (
            <nav className="flex gap-1 mt-3 -mb-4" role="tablist">
              {TABS.map(({ id, label }) => (
                <button
                  key={id}
                  role="tab"
                  aria-selected={activeTab === id}
                  onClick={() => setActiveTab(id)}
                  className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
                    activeTab === id
                      ? 'bg-gray-50 text-gray-900 border border-gray-200 border-b-gray-50'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {label}
                </button>
              ))}
            </nav>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-6 space-y-6">
        {/* File Upload */}
        <FileUpload
          onUpload={handleUpload}
          onUseSample={handleUseSample}
          onCrawl={handleCrawl}
          isLoading={isLoading}
          uploadInfo={uploadInfo}
          ratingThreshold={ratingThreshold}
          onRatingThresholdChange={handleRatingThresholdChange}
        />

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3">
            {error}
          </div>
        )}

        {/* Loading */}
        {isLoading && <LoadingSpinner />}

        {/* Results */}
        {analysisResult && !isLoading && (
          <>
            {activeTab === 'analysis' && (
              <>
                {/* KPI Metrics */}
                <MetricsOverview
                  stats={analysisResult.stats}
                  categoryCount={Object.keys(categories).length}
                />

                {/* Charts + Top Issues */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <CategoryChart allCategories={categories} />
                  <TopIssuesCard topIssues={analysisResult.top_issues} />
                </div>

                {/* Emerging Issues + Action Plan */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <EmergingIssues emergingIssues={analysisResult.emerging_issues} />
                  <ActionPlan recommendations={analysisResult.recommendations} />
                </div>

                {/* Review List */}
                <ReviewList uploadInfo={uploadInfo} />
              </>
            )}

            {activeTab === 'reply' && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2">
                  <PriorityReviewList uploadInfo={uploadInfo} />
                </div>
                <div className="lg:col-span-1">
                  <div className="sticky top-24">
                    <ReplyGuide />
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'risk' && (
              <RiskIntelligence analysisResult={analysisResult} />
            )}
          </>
        )}
      </main>
    </div>
  );
}

export default App;
