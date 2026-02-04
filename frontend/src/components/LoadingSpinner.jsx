import { useEffect, useState } from 'react';
import { Loader2, CheckCircle } from 'lucide-react';

const STEPS = [
  { label: '데이터 로딩 중...', duration: 2000 },
  { label: '부정 리뷰 필터링 중...', duration: 2000 },
  { label: '기간별 데이터 분할 중...', duration: 1500 },
  { label: 'GPT-4o-mini로 카테고리 분류 중...', duration: 8000 },
  { label: 'Top 이슈 분석 중...', duration: 2000 },
  { label: '급증 이슈 탐지 중...', duration: 2000 },
  { label: 'AI 개선 액션 생성 중...', duration: 5000 },
  { label: '결과 정리 중...', duration: 2000 },
];

export default function LoadingSpinner() {
  const [currentStep, setCurrentStep] = useState(0);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const totalDuration = STEPS.reduce((sum, step) => sum + step.duration, 0);
    let elapsed = 0;

    const interval = setInterval(() => {
      elapsed += 100;

      // 현재 단계 계산
      let accumulated = 0;
      for (let i = 0; i < STEPS.length; i++) {
        accumulated += STEPS[i].duration;
        if (elapsed < accumulated) {
          setCurrentStep(i);
          break;
        }
      }

      // 진행률 계산 (최대 95%까지만 - 실제 완료는 API 응답 시)
      const newProgress = Math.min(95, Math.round((elapsed / totalDuration) * 100));
      setProgress(newProgress);

      if (elapsed >= totalDuration) {
        clearInterval(interval);
      }
    }, 100);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
      <div className="flex flex-col items-center">
        {/* 진행률 원형 */}
        <div className="relative mb-6">
          <svg className="w-24 h-24 transform -rotate-90">
            <circle
              cx="48"
              cy="48"
              r="40"
              stroke="#e5e7eb"
              strokeWidth="8"
              fill="none"
            />
            <circle
              cx="48"
              cy="48"
              r="40"
              stroke="#3b82f6"
              strokeWidth="8"
              fill="none"
              strokeDasharray={251.2}
              strokeDashoffset={251.2 - (251.2 * progress) / 100}
              strokeLinecap="round"
              className="transition-all duration-300"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-2xl font-bold text-blue-600">{progress}%</span>
          </div>
        </div>

        {/* 현재 작업 */}
        <div className="flex items-center gap-2 mb-6">
          <Loader2 className="animate-spin text-blue-500" size={20} />
          <p className="text-lg font-medium text-gray-700">
            {STEPS[currentStep]?.label || '처리 중...'}
          </p>
        </div>

        {/* 단계 목록 */}
        <div className="w-full max-w-md space-y-2">
          {STEPS.map((step, idx) => (
            <div
              key={idx}
              className={`flex items-center gap-3 px-4 py-2 rounded-lg transition-all ${
                idx < currentStep
                  ? 'bg-green-50 text-green-700'
                  : idx === currentStep
                  ? 'bg-blue-50 text-blue-700'
                  : 'bg-gray-50 text-gray-400'
              }`}
            >
              {idx < currentStep ? (
                <CheckCircle size={18} className="text-green-500" />
              ) : idx === currentStep ? (
                <Loader2 size={18} className="animate-spin text-blue-500" />
              ) : (
                <div className="w-[18px] h-[18px] rounded-full border-2 border-gray-300" />
              )}
              <span className="text-sm font-medium">{step.label.replace('...', '')}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
