import { useEffect, useState } from 'react';
import { Loader2, CheckCircle, Radio } from 'lucide-react';

const STEPS = [
  { label: '4개 채널 신호 수신 및 클러스터링', duration: 2000 },
  { label: '온톨로지 엔진 인과관계 분석', duration: 8000 },
  { label: '컴플라이언스 리스크 보고서 생성', duration: 8000 },
  { label: '경영진 긴급 회의 안건 생성', duration: 8000 },
  { label: '결과 통합 및 리스크 레벨 산정', duration: 3000 },
];

const PARALLEL = [1, 2, 3];

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
    <div className="bg-slate-900 rounded-2xl border border-slate-800 p-8">
      <div className="flex flex-col items-center">
        {/* 원형 진행률 */}
        <div className="relative mb-6">
          <svg className="w-24 h-24 transform -rotate-90">
            <circle cx="48" cy="48" r="40" stroke="#1e293b" strokeWidth="8" fill="none" />
            <circle
              cx="48" cy="48" r="40"
              stroke="#6366f1"
              strokeWidth="8"
              fill="none"
              strokeDasharray={251.2}
              strokeDashoffset={251.2 - (251.2 * progress) / 100}
              strokeLinecap="round"
              className="transition-all duration-300"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-2xl font-bold text-indigo-400">{progress}%</span>
          </div>
        </div>

        {/* 현재 작업 */}
        <div className="flex items-center gap-2 mb-6">
          <Radio className="text-indigo-400 animate-pulse" size={16} />
          <p className="text-sm font-medium text-slate-300">
            {mode === 'demo'
              ? currentStep <= 3
                ? 'AI 엔진 병렬 분석 중...'
                : '결과 통합 중...'
              : (steps[currentStep]?.label || '분석 중...')}
          </p>
        </div>

        {/* 단계 목록 */}
        <div className="w-full max-w-md space-y-1.5">
          {steps.map((step, idx) => {
            const done = isDone(idx);
            const active = isActive(idx);
            const parallel = isParallel(idx);

            return (
              <div
                key={idx}
                className={`flex items-center gap-3 px-4 py-2 rounded-lg transition-all text-sm ${
                  done
                    ? 'bg-emerald-950/50 text-emerald-400 border border-emerald-900'
                    : active
                      ? 'bg-indigo-950/50 text-indigo-300 border border-indigo-900'
                      : 'bg-slate-800/50 text-slate-600 border border-slate-800'
                }`}
              >
                {done ? (
                  <CheckCircle size={15} className="text-emerald-400 flex-shrink-0" />
                ) : active ? (
                  <Loader2 size={15} className="animate-spin text-indigo-400 flex-shrink-0" />
                ) : (
                  <div className="w-[15px] h-[15px] rounded-full border border-slate-700 flex-shrink-0" />
                )}
                <span className="font-medium">{step.label}</span>
                {parallel && (
                  <span className="ml-auto text-[10px] text-indigo-500 font-semibold border border-indigo-900 px-1.5 rounded">병렬</span>
                )}
              </div>
            );
          })}
        </div>

        {mode === 'demo' && (
          <p className="mt-4 text-xs text-slate-600">
            온톨로지 · 컴플라이언스 · 회의안건 동시 생성 중
          </p>
        )}
      </div>
    </div>
  );
}
