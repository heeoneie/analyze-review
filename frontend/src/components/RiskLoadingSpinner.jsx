import { useEffect, useState } from 'react';
import { Loader2, CheckCircle, Radio } from 'lucide-react';

const STEPS = [
  { label: '4개 채널 신호 수신 및 클러스터링', duration: 2000 },
  { label: '온톨로지 엔진 인과관계 분석', duration: 8000 },
  { label: '컴플라이언스 리스크 보고서 생성', duration: 8000 },
  { label: '경영진 긴급 회의 안건 생성', duration: 8000 },
  { label: '결과 통합 및 리스크 레벨 산정', duration: 3000 },
];

const PARALLEL = [1, 2, 3]; // 인덱스 1~3은 병렬

export default function RiskLoadingSpinner({ mode = 'demo' }) {
  const [currentStep, setCurrentStep] = useState(0);
  const [progress, setProgress] = useState(0);

  const steps = mode === 'single'
    ? [
        { label: '분석 데이터 수집 중', duration: 2000 },
        { label: 'AI 분석 실행 중', duration: 10000 },
        { label: '결과 정리 중', duration: 2000 },
      ]
    : STEPS;

  useEffect(() => {
    const totalDuration = steps.reduce((sum, s) => sum + s.duration, 0);
    let elapsed = 0;

    const interval = setInterval(() => {
      elapsed += 100;

      let accumulated = 0;
      for (let i = 0; i < steps.length; i++) {
        accumulated += steps[i].duration;
        if (elapsed < accumulated) {
          setCurrentStep(i);
          break;
        }
        if (i === steps.length - 1) setCurrentStep(i);
      }

      setProgress(Math.min(95, Math.round((elapsed / totalDuration) * 100)));

      if (elapsed >= totalDuration) clearInterval(interval);
    }, 100);

    return () => clearInterval(interval);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isParallel = (idx) => mode === 'demo' && PARALLEL.includes(idx);
  const isActive = (idx) =>
    isParallel(idx) ? currentStep >= 1 && currentStep <= 3 : idx === currentStep;
  const isDone = (idx) =>
    isParallel(idx) ? currentStep > 3 : idx < currentStep;

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
      <div className="flex flex-col items-center">
        {/* 원형 진행률 */}
        <div className="relative mb-6">
          <svg className="w-24 h-24 transform -rotate-90">
            <circle cx="48" cy="48" r="40" stroke="#e5e7eb" strokeWidth="8" fill="none" />
            <circle
              cx="48" cy="48" r="40"
              stroke="#8B5CF6"
              strokeWidth="8"
              fill="none"
              strokeDasharray={251.2}
              strokeDashoffset={251.2 - (251.2 * progress) / 100}
              strokeLinecap="round"
              className="transition-all duration-300"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-2xl font-bold text-purple-600">{progress}%</span>
          </div>
        </div>

        {/* 현재 작업 */}
        <div className="flex items-center gap-2 mb-6">
          <Radio className="text-purple-500 animate-pulse" size={18} />
          <p className="text-base font-medium text-gray-700">
            {mode === 'demo'
              ? currentStep <= 3
                ? 'AI 엔진 병렬 분석 중...'
                : '결과 통합 중...'
              : (steps[currentStep]?.label || '분석 중...')}
          </p>
        </div>

        {/* 단계 목록 */}
        <div className="w-full max-w-md space-y-2">
          {steps.map((step, idx) => {
            const done = isDone(idx);
            const active = isActive(idx);
            const parallel = isParallel(idx);

            return (
              <div
                key={idx}
                className={`flex items-center gap-3 px-4 py-2 rounded-lg transition-all ${
                  done
                    ? 'bg-green-50 text-green-700'
                    : active
                      ? 'bg-purple-50 text-purple-700'
                      : 'bg-gray-50 text-gray-400'
                }`}
              >
                {done ? (
                  <CheckCircle size={18} className="text-green-500 flex-shrink-0" />
                ) : active ? (
                  <Loader2 size={18} className="animate-spin text-purple-500 flex-shrink-0" />
                ) : (
                  <div className="w-[18px] h-[18px] rounded-full border-2 border-gray-300 flex-shrink-0" />
                )}
                <span className="text-sm font-medium">{step.label}</span>
                {parallel && (
                  <span className="ml-auto text-xs text-purple-400 font-medium">병렬</span>
                )}
              </div>
            );
          })}
        </div>

        {mode === 'demo' && (
          <p className="mt-4 text-xs text-gray-400">
            온톨로지 · 컴플라이언스 · 회의안건을 동시 생성 중
          </p>
        )}
      </div>
    </div>
  );
}
