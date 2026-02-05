import { useState } from 'react';
import {
  uploadCSV,
  useSampleData,
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
import './index.css';

function App() {
  const [uploadInfo, setUploadInfo] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [ratingThreshold, setRatingThreshold] = useState(3);

  const handleRatingThresholdChange = async (value) => {
    setRatingThreshold(value);
    try {
      await updateSettings(value);
    } catch (err) {
      console.error('설정 업데이트 실패:', err);
    }
  };

  const handleUpload = async (file) => {
    try {
      setError(null);
      setIsLoading(true);
      const { data } = await uploadCSV(file);
      setUploadInfo(data);
      const result = await runAnalysis();
      setAnalysisResult(result.data);
    } catch (err) {
      setError(err.response?.data?.detail || '분석 중 오류가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleUseSample = async () => {
    try {
      setError(null);
      setIsLoading(true);
      const { data } = await useSampleData();
      setUploadInfo(data);
      const result = await runAnalysis();
      setAnalysisResult(result.data);
    } catch (err) {
      setError(err.response?.data?.detail || '분석 중 오류가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCrawl = async (url) => {
    try {
      setError(null);
      setIsLoading(true);
      const { data } = await crawlReviews(url);
      setUploadInfo(data);
      const result = await runAnalysis();
      setAnalysisResult(result.data);
    } catch (err) {
      setError(err.response?.data?.detail || '크롤링 중 오류가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <h1 className="text-xl font-bold text-gray-900">
            E-commerce Review Analysis Dashboard
          </h1>
          <p className="text-sm text-gray-500">LLM 기반 리뷰 자동 분류 및 컨설팅 시스템</p>
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
            {/* KPI Metrics */}
            <MetricsOverview
              stats={analysisResult.stats}
              categoryCount={Object.keys(analysisResult.all_categories).length}
            />

            {/* Charts + Top Issues */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <CategoryChart allCategories={analysisResult.all_categories} />
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
      </main>
    </div>
  );
}

export default App;
