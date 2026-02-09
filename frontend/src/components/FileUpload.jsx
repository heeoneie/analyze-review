import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, Database, Link, Loader2, Star } from 'lucide-react';

export default function FileUpload({
  onUpload,
  onUseSample,
  onCrawl,
  isLoading,
  uploadInfo,
  ratingThreshold,
  onRatingThresholdChange,
}) {
  const [crawlUrl, setCrawlUrl] = useState('');
  const [activeTab, setActiveTab] = useState('upload'); // 'upload' | 'crawl'

  const onDrop = useCallback(
    (acceptedFiles) => {
      if (acceptedFiles.length > 0) {
        onUpload(acceptedFiles[0]);
      }
    },
    [onUpload]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'text/csv': ['.csv'] },
    maxFiles: 1,
    disabled: isLoading,
  });

  const handleCrawl = () => {
    const trimmed = crawlUrl.trim();
    if (trimmed) {
      try {
        new URL(trimmed);
        onCrawl(trimmed);
      } catch {
        alert('올바른 URL을 입력해주세요.');
      }
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
      {/* 탭 선택 */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setActiveTab('upload')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === 'upload'
              ? 'bg-blue-500 text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          <Upload size={16} className="inline mr-2" />
          CSV 업로드
        </button>
        <button
          onClick={() => setActiveTab('crawl')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === 'crawl'
              ? 'bg-blue-500 text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          <Link size={16} className="inline mr-2" />
          URL 크롤링
        </button>
      </div>

      {/* CSV 업로드 탭 */}
      {activeTab === 'upload' && (
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all
            ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-blue-300 hover:bg-gray-50'}
            ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          <input {...getInputProps()} />
          <Upload className="mx-auto mb-3 text-gray-400" size={36} />
          {isDragActive ? (
            <p className="text-blue-600 font-medium">파일을 놓아주세요</p>
          ) : (
            <>
              <p className="text-gray-600 font-medium">CSV 파일을 드래그하거나 클릭하여 업로드</p>
              <p className="text-gray-400 text-sm mt-1">Ratings, Reviews 컬럼이 포함된 CSV</p>
            </>
          )}
        </div>
      )}

      {/* URL 크롤링 탭 */}
      {activeTab === 'crawl' && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">상품 URL</label>
            <input
              type="url"
              value={crawlUrl}
              onChange={(e) => setCrawlUrl(e.target.value)}
              placeholder="쿠팡 또는 네이버 스마트스토어 상품 URL을 입력하세요"
              disabled={isLoading}
              className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
            />
            <p className="text-xs text-gray-400 mt-1">
              지원: 쿠팡 (coupang.com), 네이버 스마트스토어 (smartstore.naver.com)
            </p>
          </div>
          <button
            onClick={handleCrawl}
            disabled={isLoading || !crawlUrl.trim()}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-500 hover:bg-blue-600 text-white rounded-xl font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                크롤링 중...
              </>
            ) : (
              <>
                <Link size={18} />
                리뷰 가져오기
              </>
            )}
          </button>
        </div>
      )}

      {/* 설정 및 액션 */}
      <div className="mt-4 pt-4 border-t border-gray-100">
        <div className="flex flex-wrap items-center gap-4">
          {/* 별점 기준 설정 */}
          <div className="flex items-center gap-2">
            <Star size={16} className="text-yellow-500" />
            <span className="text-sm text-gray-600">부정 리뷰 기준:</span>
            <select
              value={ratingThreshold}
              onChange={(e) => onRatingThresholdChange(Number(e.target.value))}
              disabled={isLoading}
              className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value={1}>1점 이하</option>
              <option value={2}>2점 이하</option>
              <option value={3}>3점 이하</option>
              <option value={4}>4점 이하</option>
            </select>
          </div>

          {/* 샘플 데이터 버튼 */}
          <button
            onClick={onUseSample}
            disabled={isLoading}
            className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm font-medium text-gray-700 transition-colors disabled:opacity-50"
          >
            <Database size={16} />
            샘플 데이터로 분석
          </button>

          {/* 업로드 정보 */}
          {uploadInfo && (
            <span className="text-sm text-green-600 font-medium">
              {uploadInfo.filename || uploadInfo.platform} ({uploadInfo.total_rows}개 리뷰)
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
