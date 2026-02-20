import { useState } from 'react';
import { useLang } from './contexts/LangContext';
import RiskIntelligence from './components/RiskIntelligence';
import './index.css';

const TABS = [
  { id: 'risk',     labelKey: 'tabs.risk',     soon: false },
  { id: 'playbook', labelKey: 'tabs.playbook', soon: true },
  { id: 'agent',    labelKey: 'tabs.agent',    soon: true },
];

function App() {
  const { lang, setLang, t } = useLang();
  const [activeTab, setActiveTab] = useState('risk');
  const currentTab = TABS.find((tab) => tab.id === activeTab) || TABS[0];

  return (
    <div className="min-h-screen bg-zinc-950">
      <header className="bg-zinc-900 border-b border-zinc-800 sticky top-0 z-10">

        {/* Row 1: Breadcrumb + LIVE + Lang toggle */}
        <div className="max-w-7xl mx-auto px-6 py-2.5 flex items-center justify-between border-b border-zinc-800/50">
          <nav className="flex items-center gap-2 text-xs" aria-label="breadcrumb">
            <span className="font-bold text-white tracking-tight">OntoReview</span>
            <span className="text-zinc-700">/</span>
            <span className="text-zinc-500">{t('tabs.riskMgmt')}</span>
            <span className="text-zinc-700">/</span>
            <span className="text-zinc-300 font-medium">{t(currentTab.labelKey)}</span>
          </nav>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className="relative flex h-1.5 w-1.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-50" />
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-400" />
              </span>
              <span className="text-xs text-emerald-400 font-bold tracking-widest">LIVE</span>
            </div>
            <button
              onClick={() => setLang(lang === 'ko' ? 'en' : 'ko')}
              className="px-2.5 py-1 text-xs font-bold text-zinc-400 border border-zinc-700 rounded-md hover:bg-zinc-800 hover:text-zinc-200 transition-colors"
            >
              {lang === 'ko' ? 'EN' : '한'}
            </button>
          </div>
        </div>

        {/* Row 2: Tab navigation — underline style */}
        <div className="max-w-7xl mx-auto px-6">
          <nav className="flex" role="tablist">
            {TABS.map(({ id, labelKey, soon }) => (
              <button
                key={id}
                role="tab"
                aria-selected={activeTab === id}
                disabled={soon}
                onClick={() => !soon && setActiveTab(id)}
                className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
                  activeTab === id
                    ? 'border-white text-white'
                    : soon
                      ? 'border-transparent text-zinc-600 cursor-not-allowed'
                      : 'border-transparent text-zinc-500 hover:text-zinc-300 hover:border-zinc-600'
                }`}
              >
                {t(labelKey)}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6">
        {activeTab === 'risk' && <RiskIntelligence />}
      </main>
    </div>
  );
}

export default App;
