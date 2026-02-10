import { useState, useEffect } from 'react';
import {
  BookOpen,
  ChevronDown,
  ChevronUp,
  ThumbsUp,
  ThumbsDown,
  Target,
  Volume2,
  ListOrdered,
  Loader2,
} from 'lucide-react';
import { getReplyGuide, getAllGuides } from '../api/client';

function GuideDetail({ guide }) {
  const [showExamples, setShowExamples] = useState(false);

  if (!guide) return null;

  return (
    <div className="space-y-4">
      {/* 권장 어조 */}
      <div className="bg-blue-50 rounded-lg p-3">
        <div className="flex items-center gap-1.5 text-sm font-medium text-blue-700 mb-1">
          <Volume2 size={14} />
          권장 어조
        </div>
        <p className="text-sm text-blue-800">{guide.tone}</p>
      </div>

      {/* 답변 구조 */}
      <div>
        <div className="flex items-center gap-1.5 text-sm font-medium text-gray-700 mb-2">
          <ListOrdered size={14} />
          답변 구조
        </div>
        <ol className="space-y-1.5">
          {guide.structure?.map((step, i) => (
            <li key={i} className="flex gap-2 text-sm text-gray-600">
              <span className="flex-shrink-0 w-5 h-5 bg-gray-100 rounded-full text-xs flex items-center justify-center font-medium text-gray-500">
                {i + 1}
              </span>
              {step}
            </li>
          ))}
        </ol>
      </div>

      {/* 필수 포인트 */}
      <div>
        <div className="flex items-center gap-1.5 text-sm font-medium text-gray-700 mb-2">
          <Target size={14} />
          반드시 다뤄야 할 포인트
        </div>
        <ul className="space-y-1">
          {guide.must_address?.map((point, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
              <span className="text-green-500 mt-0.5">&#10003;</span>
              {point}
            </li>
          ))}
        </ul>
      </div>

      {/* 예시 토글 */}
      <button
        onClick={() => setShowExamples(!showExamples)}
        className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors w-full"
      >
        {showExamples ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        {showExamples ? '예시 접기' : '좋은/나쁜 예시 보기'}
      </button>

      {showExamples && (
        <div className="space-y-3">
          {guide.good_example && (
            <div className="bg-green-50 border border-green-100 rounded-lg p-3">
              <div className="flex items-center gap-1.5 text-xs font-medium text-green-700 mb-1.5">
                <ThumbsUp size={12} />
                좋은 예시
              </div>
              <p className="text-sm text-green-800 leading-relaxed">
                {guide.good_example}
              </p>
            </div>
          )}
          {guide.bad_example && (
            <div className="bg-red-50 border border-red-100 rounded-lg p-3">
              <div className="flex items-center gap-1.5 text-xs font-medium text-red-700 mb-1.5">
                <ThumbsDown size={12} />
                나쁜 예시 (매크로)
              </div>
              <p className="text-sm text-red-800 leading-relaxed">
                {guide.bad_example}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ReplyGuide({ activeCategory }) {
  const [allGuides, setAllGuides] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [guideData, setGuideData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // 전체 가이드 목록 로드
  useEffect(() => {
    getAllGuides()
      .then(({ data }) => setAllGuides(data.guides || []))
      .catch(() => {});
  }, []);

  // activeCategory가 변경되면 자동으로 해당 가이드 로드
  useEffect(() => {
    if (activeCategory && activeCategory !== selectedCategory) {
      setSelectedCategory(activeCategory);
      loadGuide(activeCategory);
    }
  }, [activeCategory]);

  const loadGuide = async (category) => {
    setIsLoading(true);
    try {
      const { data } = await getReplyGuide(category);
      setGuideData(data);
      setSelectedCategory(category);
    } catch {
      setGuideData(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCategoryClick = (category) => {
    if (selectedCategory === category && guideData) {
      // 이미 선택된 카테고리면 토글
      setSelectedCategory(null);
      setGuideData(null);
    } else {
      loadGuide(category);
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
      <div className="flex items-center gap-2 mb-4">
        <BookOpen className="text-indigo-500" size={18} />
        <h3 className="text-base font-semibold text-gray-900">답변 품질 가이드</h3>
      </div>

      {/* 카테고리 칩 */}
      <div className="flex flex-wrap gap-1.5 mb-4">
        {allGuides.map(({ category }) => (
          <button
            key={category}
            onClick={() => handleCategoryClick(category)}
            className={`px-2.5 py-1 text-xs rounded-full transition-colors ${
              selectedCategory === category
                ? 'bg-indigo-100 text-indigo-700 font-medium'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {category}
          </button>
        ))}
      </div>

      {/* 가이드 내용 */}
      {isLoading ? (
        <div className="flex items-center justify-center gap-2 py-8 text-gray-400">
          <Loader2 size={16} className="animate-spin" />
          <span className="text-sm">가이드 로딩 중...</span>
        </div>
      ) : guideData ? (
        <>
          {guideData.source === 'generated' && (
            <div className="text-xs text-amber-600 bg-amber-50 rounded-lg px-3 py-1.5 mb-3">
              AI가 자동 생성한 가이드입니다
            </div>
          )}
          <GuideDetail guide={guideData} />
        </>
      ) : (
        <p className="text-sm text-gray-400 text-center py-6">
          카테고리를 선택하면 답변 작성 가이드가 표시됩니다
        </p>
      )}
    </div>
  );
}
