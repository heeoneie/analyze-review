import { useEffect, useRef, useState } from 'react';
import { ShieldCheck, MessageSquare, Scale, Loader2, AlertTriangle, ArrowLeft, Network } from 'lucide-react';
import { generatePlaybook } from '../api/client';
import { useLang } from '../contexts/LangContext';

const STRATEGY_CONFIG = {
  Conservative: {
    icon: ShieldCheck,
    border: 'border-emerald-700/60',
    glow: 'shadow-[0_0_20px_rgba(16,185,129,0.08)]',
    badge: 'bg-emerald-500/15 text-emerald-400 border-emerald-700/50',
    accent: 'text-emerald-400',
    labelKey: 'playbook.conservative',
    descKey: 'playbook.conservativeDesc',
  },
  Moderate: {
    icon: MessageSquare,
    border: 'border-amber-700/60',
    glow: 'shadow-[0_0_20px_rgba(245,158,11,0.08)]',
    badge: 'bg-amber-500/15 text-amber-400 border-amber-700/50',
    accent: 'text-amber-400',
    labelKey: 'playbook.moderate',
    descKey: 'playbook.moderateDesc',
  },
  Aggressive: {
    icon: Scale,
    border: 'border-rose-700/60',
    glow: 'shadow-[0_0_20px_rgba(225,29,72,0.08)]',
    badge: 'bg-rose-500/15 text-rose-400 border-rose-700/50',
    accent: 'text-rose-400',
    labelKey: 'playbook.aggressive',
    descKey: 'playbook.aggressiveDesc',
  },
};

function SkeletonCard() {
  return (
    <div className="bg-zinc-900/80 backdrop-blur-sm border border-zinc-800 rounded-2xl p-6 animate-pulse">
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 rounded-xl bg-zinc-800" />
        <div className="space-y-2 flex-1">
          <div className="h-4 w-28 bg-zinc-800 rounded" />
          <div className="h-3 w-44 bg-zinc-800/60 rounded" />
        </div>
      </div>
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-10 bg-zinc-800/60 rounded-lg" />
        ))}
      </div>
      <div className="mt-5 h-16 bg-zinc-800/40 rounded-lg" />
    </div>
  );
}

export default function RiskPlaybook({ nodeName, industry, onBack }) {
  const { t, lang } = useLang();
  const [scenarios, setScenarios] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const controllerRef = useRef(null);

  const selectedNodeName = (nodeName ?? '').trim();
  const hasNode = selectedNodeName.length > 0;

  useEffect(() => {
    if (!hasNode) {
      setIsLoading(false);
      setScenarios(null);
      setError(null);
      return;
    }

    const controller = new AbortController();
    controllerRef.current = controller;

    setIsLoading(true);
    setError(null);
    setScenarios(null);

    generatePlaybook({
      node_name: selectedNodeName,
      industry: industry || 'ecommerce',
      lang,
    })
      .then((res) => {
        if (!controller.signal.aborted) {
          setScenarios(res.data?.scenarios ?? []);
        }
      })
      .catch((err) => {
        if (!controller.signal.aborted) {
          setError(err.response?.data?.detail || t('playbook.error'));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      });

    return () => {
      controller.abort();
    };
  }, [selectedNodeName, industry, lang]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleRetry = () => {
    if (!hasNode) return;

    setIsLoading(true);
    setError(null);
    setScenarios(null);

    generatePlaybook({
      node_name: selectedNodeName,
      industry: industry || 'ecommerce',
      lang,
    })
      .then((res) => setScenarios(res.data?.scenarios ?? []))
      .catch((err) => setError(err.response?.data?.detail || t('playbook.error')))
      .finally(() => setIsLoading(false));
  };

  /* ── Empty State: no node selected ── */
  if (!hasNode) {
    return (
      <div className="min-h-[600px] p-6 flex items-center justify-center">
        <div className="flex flex-col items-center gap-5 max-w-md text-center">
          <div className="w-20 h-20 rounded-2xl bg-zinc-900 border border-zinc-800 flex items-center justify-center">
            <Network size={36} className="text-zinc-600" />
          </div>
          <div className="space-y-2">
            <h2 className="text-xl font-semibold text-zinc-200">
              {t('playbook.emptyTitle')}
            </h2>
            <p className="text-sm text-zinc-500 leading-relaxed">
              {t('playbook.emptyDesc')}
            </p>
          </div>
          {onBack && (
            <button
              type="button"
              onClick={onBack}
              className="flex items-center gap-2 bg-zinc-800 hover:bg-zinc-700 text-white font-semibold text-sm px-5 py-2.5 rounded-lg transition-colors"
            >
              <ArrowLeft size={15} />
              {t('playbook.goToGraph')}
            </button>
          )}
        </div>
      </div>
    );
  }

  /* ── Normal State: node selected ── */
  return (
    <div className="min-h-[600px] p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-bold text-white">{t('playbook.title')}</h2>
          <p className="text-sm text-zinc-500 mt-0.5">{t('playbook.subtitle')}</p>
        </div>
        {onBack && (
          <button
            type="button"
            onClick={onBack}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-zinc-400
              bg-zinc-800 border border-zinc-700 rounded-lg hover:bg-zinc-700 hover:text-zinc-200 transition-colors"
          >
            <ArrowLeft size={13} />
            {t('playbook.backToGraph')}
          </button>
        )}
      </div>

      {/* Context badges */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-zinc-800 border border-zinc-700 text-xs font-medium text-zinc-300">
          {t('playbook.targetNode')}: {selectedNodeName}
        </span>
        {industry && (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-zinc-800 border border-zinc-700 text-xs font-medium text-zinc-400">
            {t('playbook.industry')}: {industry}
          </span>
        )}
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="space-y-4">
          <div className="flex items-center gap-3 bg-zinc-900 rounded-xl border border-zinc-800 px-5 py-4">
            <Loader2 className="animate-spin text-indigo-400" size={20} />
            <div>
              <p className="text-sm font-medium text-white">{t('playbook.loading')}</p>
              <p className="text-xs text-zinc-500 mt-0.5">{t('playbook.loadingHint')}</p>
            </div>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
        </div>
      )}

      {/* Error state */}
      {error && !isLoading && (
        <div className="bg-red-950/40 border border-red-800/60 rounded-xl px-5 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AlertTriangle className="text-red-400" size={18} />
            <p className="text-sm text-red-400">{error}</p>
          </div>
          <button
            type="button"
            onClick={handleRetry}
            className="px-3 py-1.5 text-xs font-semibold text-red-400 bg-red-950 border border-red-800 rounded-lg hover:bg-red-900 transition-colors"
          >
            {t('playbook.retry')}
          </button>
        </div>
      )}

      {/* Scenario cards */}
      {scenarios && scenarios.length > 0 && !isLoading && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {scenarios.map((scenario) => {
            const cfg = STRATEGY_CONFIG[scenario.strategy_name] || STRATEGY_CONFIG.Moderate;
            const Icon = cfg.icon;

            return (
              <div
                key={scenario.strategy_name}
                className={`bg-zinc-900/80 backdrop-blur-sm border ${cfg.border} rounded-2xl p-6 ${cfg.glow} transition-shadow hover:shadow-lg`}
              >
                {/* Card header */}
                <div className="flex items-center gap-3 mb-5">
                  <div className={`w-10 h-10 rounded-xl border ${cfg.border} bg-zinc-800/80 flex items-center justify-center`}>
                    <Icon size={18} className={cfg.accent} />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-zinc-100">
                      {t(cfg.labelKey)}
                    </h3>
                    <p className="text-[11px] text-zinc-500">
                      {t(cfg.descKey)}
                    </p>
                  </div>
                </div>

                {/* Agent badge */}
                <div className="mb-4">
                  <span className="text-[10px] text-zinc-600 uppercase tracking-wider font-medium">
                    {t('playbook.agent')}
                  </span>
                  <div className="mt-1">
                    <span className={`inline-flex items-center px-2.5 py-1 text-xs font-semibold rounded-full border ${cfg.badge}`}>
                      {scenario.primary_agent}
                    </span>
                  </div>
                </div>

                {/* Action steps */}
                <div className="mb-4">
                  <span className="text-[10px] text-zinc-600 uppercase tracking-wider font-medium">
                    {t('playbook.steps')}
                  </span>
                  <ol className="mt-2 space-y-2">
                    {scenario.action_steps.map((step, i) => (
                      <li key={i} className="flex gap-2.5 text-xs text-zinc-300 leading-relaxed">
                        <span className={`flex-shrink-0 w-5 h-5 rounded-full border ${cfg.border} bg-zinc-800 flex items-center justify-center text-[10px] font-bold ${cfg.accent}`}>
                          {i + 1}
                        </span>
                        <span className="pt-0.5">{step}</span>
                      </li>
                    ))}
                  </ol>
                </div>

                {/* Estimated impact */}
                <div className="mt-auto pt-4 border-t border-zinc-800/60">
                  <span className="text-[10px] text-zinc-600 uppercase tracking-wider font-medium">
                    {t('playbook.impact')}
                  </span>
                  <p className="mt-1.5 text-xs text-zinc-400 leading-relaxed">
                    {scenario.estimated_impact}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
