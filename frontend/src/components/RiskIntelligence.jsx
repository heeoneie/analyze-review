import { useState, useRef } from 'react';
import { Shield, Loader2, Radio, Building2, Zap, Share2, Download, Search, ScanSearch } from 'lucide-react';
import {
  generateOntology,
  generateComplianceReport,
  generateMeetingAgenda,
  runDemoScenario,
} from '../api/client';
import { useLang } from '../contexts/LangContext';
import OntologyGraph from './OntologyGraph';
import ComplianceReport from './ComplianceReport';
import MeetingAgenda from './MeetingAgenda';
import MockScenario from './MockScenario';
import RiskLoadingSpinner from './RiskLoadingSpinner';

const INDUSTRIES = [
  { id: 'ecommerce', labelKey: 'risk.ecommerce', icon: '🛒' },
  { id: 'hospital',  labelKey: 'risk.hospital',  icon: '🏥' },
  { id: 'finance',   labelKey: 'risk.finance',   icon: '🏦' },
  { id: 'gaming',    labelKey: 'risk.gaming',    icon: '🎮' },
];

const INDUSTRY_INPUT_CFG = {
  ecommerce: { labelKey1: 'risk.label1_ecommerce', default1: '넥서스',       labelKey2: 'risk.label2_ecommerce', default2: '파워 충전기 65W' },
  hospital:  { labelKey1: 'risk.label1_hospital',  default1: '한빛의료재단', labelKey2: 'risk.label2_hospital',  default2: '무릎 인공관절 수술' },
  finance:   { labelKey1: 'risk.label1_finance',   default1: '페이트러스트', labelKey2: 'risk.label2_finance',   default2: '간편결제 앱 v3.0' },
  gaming:    { labelKey1: 'risk.label1_gaming',    default1: '크로노게임즈', labelKey2: 'risk.label2_gaming',    default2: '크로노워 모바일' },
};

const CHANNELS_BY_INDUSTRY = {
  ecommerce: [
    { nameKey: 'risk.chEcommerce',  status: 'active' },
    { nameKey: 'risk.chNaver',      status: 'active' },
    { nameKey: 'risk.chYoutube',    status: 'active' },
    { nameKey: 'risk.chCommunity',  status: 'active' },
  ],
  hospital: [
    { nameKey: 'risk.chHospitalReview', status: 'active' },
    { nameKey: 'risk.chNaver',          status: 'active' },
    { nameKey: 'risk.chYoutube',        status: 'active' },
    { nameKey: 'risk.chCommunity',      status: 'active' },
  ],
  finance: [
    { nameKey: 'risk.chFinanceReview', status: 'active' },
    { nameKey: 'risk.chNaver',         status: 'active' },
    { nameKey: 'risk.chYoutube',       status: 'active' },
    { nameKey: 'risk.chCommunity',     status: 'active' },
  ],
  gaming: [
    { nameKey: 'risk.chGamingReview', status: 'active' },
    { nameKey: 'risk.chYoutube',      status: 'active' },
    { nameKey: 'risk.chCommunity',    status: 'active' },
    { nameKey: 'risk.chNaver',        status: 'active' },
  ],
};

const EXTRA_CHANNELS_BY_INDUSTRY = {
  ecommerce: [
    { id: 'amazon',    nameKey: 'risk.chAmazon' },
    { id: 'reddit',    nameKey: 'risk.chReddit' },
    { id: 'walmart',   nameKey: 'risk.chWalmart' },
    { id: 'twitter',   nameKey: 'risk.chTwitter' },
    { id: 'instagram', nameKey: 'risk.chInstagram' },
  ],
  hospital: [
    { id: 'healthgrades', nameKey: 'risk.chHealthgrades' },
    { id: 'redditmed',    nameKey: 'risk.chRedditMed' },
    { id: 'zocdoc',       nameKey: 'risk.chZocdoc' },
    { id: 'twitter',      nameKey: 'risk.chTwitter' },
    { id: 'instagram',    nameKey: 'risk.chInstagram' },
  ],
  finance: [
    { id: 'trustpilot',  nameKey: 'risk.chTrustpilot' },
    { id: 'redditfin',   nameKey: 'risk.chRedditFin' },
    { id: 'googleplay',  nameKey: 'risk.chGooglePlay' },
    { id: 'twitter',     nameKey: 'risk.chTwitter' },
    { id: 'instagram',   nameKey: 'risk.chInstagram' },
  ],
  gaming: [
    { id: 'steam',       nameKey: 'risk.chSteam' },
    { id: 'metacritic',  nameKey: 'risk.chMetacritic' },
    { id: 'twitch',      nameKey: 'risk.chTwitch' },
    { id: 'redditgame',  nameKey: 'risk.chRedditGame' },
    { id: 'twitter',     nameKey: 'risk.chTwitter' },
  ],
};

const RISK_LEVEL_CONFIG = {
  GREEN:  { labelKey: 'risk.safe',     dot: 'bg-emerald-400', text: 'text-emerald-400', banner: 'bg-emerald-950/40 border-emerald-800' },
  YELLOW: { labelKey: 'risk.caution',  dot: 'bg-amber-400',   text: 'text-amber-400',   banner: 'bg-amber-950/40 border-amber-800' },
  ORANGE: { labelKey: 'risk.warning',  dot: 'bg-orange-400',  text: 'text-orange-400',  banner: 'bg-orange-950/40 border-orange-800' },
  RED:    { labelKey: 'risk.critical', dot: 'bg-red-500',     text: 'text-red-400',     banner: 'bg-red-950/40 border-red-800' },
};

function RiskLevelBanner({ level }) {
  const { t } = useLang();
  if (!level) return null;
  const cfg = RISK_LEVEL_CONFIG[level] || RISK_LEVEL_CONFIG.GREEN;
  const label = t(cfg.labelKey);
  return (
    <div className={`flex items-center gap-3 px-4 py-3 rounded-xl border ${cfg.banner}`}>
      <span className="relative flex h-3 w-3 flex-shrink-0">
        {(level === 'RED' || level === 'ORANGE') && (
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${cfg.dot} opacity-50`} />
        )}
        <span className={`relative inline-flex rounded-full h-3 w-3 ${cfg.dot}`} />
      </span>
      <span className={`text-sm font-semibold ${cfg.text}`}>
        {t('risk.currentRisk')} {label}
        {level === 'RED' && ` — ${t('risk.redAlert')}`}
        {level === 'ORANGE' && ` — ${t('risk.orangeAlert')}`}
      </span>
      <span className={`ml-auto text-xs font-bold px-3 py-1 rounded-full border ${cfg.banner} ${cfg.text}`}>
        {label}
      </span>
    </div>
  );
}

// "OO" 플레이스홀더를 브랜드명으로 교체
function injectBrand(obj, brand) {
  if (!brand || !obj) return obj;
  return JSON.parse(JSON.stringify(obj).replace(/OO/g, brand));
}

export default function RiskIntelligence({ analysisResult }) {
  const { t } = useLang();
  const [demoResult, setDemoResult] = useState(null);
  const [ontology, setOntology] = useState(null);
  const [compliance, setCompliance] = useState(null);
  const [meeting, setMeeting] = useState(null);
  const [riskLevel, setRiskLevel] = useState(null);
  const [loading, setLoading] = useState({ demo: false, all: false, ontology: false, compliance: false, meeting: false });
  const [errors, setErrors] = useState({});
  const [industry, setIndustry] = useState('ecommerce');
  const [shareDropdown, setShareDropdown] = useState(false);
  const [shareToast, setShareToast] = useState('');
  const [brandName, setBrandName] = useState(INDUSTRY_INPUT_CFG.ecommerce.default1);
  const [productName, setProductName] = useState(INDUSTRY_INPUT_CFG.ecommerce.default2);
  const [scanPhase, setScanPhase] = useState(false);
  const [selectedExtra, setSelectedExtra] = useState(new Set());
  const inputRef = useRef(null);

  const toggleExtra = (id) => {
    setSelectedExtra((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else if (next.size < 5) next.add(id);
      return next;
    });
  };

  const analysisData = {
    top_issues: analysisResult?.top_issues || [],
    emerging_issues: analysisResult?.emerging_issues || [],
    recommendations: analysisResult?.recommendations || [],
    all_categories: analysisResult?.all_categories || {},
    stats: analysisResult?.stats || {},
    industry,
  };

  const handleDemo = async () => {
    const brand = [brandName.trim(), productName.trim()].filter(Boolean).join(' ') || 'OO';
    setScanPhase(true);
    setErrors({});
    setDemoResult(null);
    setOntology(null);
    setCompliance(null);
    setMeeting(null);
    setRiskLevel(null);
    await new Promise((r) => setTimeout(r, 1500));
    setScanPhase(false);
    setLoading((prev) => ({ ...prev, demo: true }));
    try {
      const res = await runDemoScenario(industry);
      const raw = res.data;
      const data = injectBrand(raw, brand);
      setDemoResult(data);
      setRiskLevel(data.risk_level);
      if (data.ontology) setOntology(data.ontology);
      if (data.compliance) setCompliance(data.compliance);
      if (data.meeting) setMeeting(data.meeting);
    } catch (err) {
      setErrors({ demo: err.response?.data?.detail || '데모 시나리오 분석 실패' });
    } finally {
      setLoading((prev) => ({ ...prev, demo: false }));
    }
  };

  const runAll = async () => {
    setLoading((prev) => ({ ...prev, all: true }));
    setErrors({});
    setDemoResult(null);
    try {
      const [ontRes, compRes, meetRes] = await Promise.allSettled([
        generateOntology(analysisData),
        generateComplianceReport(analysisData),
        generateMeetingAgenda(analysisData),
      ]);
      if (ontRes.status === 'fulfilled') setOntology(ontRes.value.data);
      else setErrors((prev) => ({ ...prev, ontology: '온톨로지 생성 실패' }));
      if (compRes.status === 'fulfilled') {
        setCompliance(compRes.value.data);
        const lvl = compRes.value.data?.overall_risk_level;
        if (lvl === '위험') setRiskLevel('RED');
        else if (lvl === '경고') setRiskLevel('ORANGE');
        else if (lvl === '주의') setRiskLevel('YELLOW');
        else setRiskLevel('GREEN');
      } else setErrors((prev) => ({ ...prev, compliance: '보고서 생성 실패' }));
      if (meetRes.status === 'fulfilled') setMeeting(meetRes.value.data);
      else setErrors((prev) => ({ ...prev, meeting: '회의 안건 생성 실패' }));
    } finally {
      setLoading((prev) => ({ ...prev, all: false }));
    }
  };

  const runSingle = async (type) => {
    setLoading((prev) => ({ ...prev, [type]: true }));
    setErrors((prev) => ({ ...prev, [type]: null }));
    try {
      if (type === 'ontology') { const res = await generateOntology(analysisData); setOntology(res.data); }
      else if (type === 'compliance') { const res = await generateComplianceReport(analysisData); setCompliance(res.data); }
      else if (type === 'meeting') { const res = await generateMeetingAgenda(analysisData); setMeeting(res.data); }
    } catch {
      setErrors((prev) => ({ ...prev, [type]: `${type} 생성 실패` }));
    } finally {
      setLoading((prev) => ({ ...prev, [type]: false }));
    }
  };

  const SHARE_TARGETS = [
    { id: 'legal',     labelKey: 'risk.shareLegal',     toastKey: 'risk.shareToastLegal' },
    { id: 'marketing', labelKey: 'risk.shareMarketing', toastKey: 'risk.shareToastMarketing' },
    { id: 'clevel',    labelKey: 'risk.shareClevel',    toastKey: 'risk.shareToastClevel' },
    { id: 'all',       labelKey: 'risk.shareAll',       toastKey: 'risk.shareToastAll' },
  ];

  const handleShare = (target) => {
    setShareDropdown(false);
    setShareToast(t(target.toastKey));
    setTimeout(() => setShareToast(''), 2500);
  };

  const handleDownload = () => {
    window.print();
  };

  const isAnyLoading = Object.values(loading).some(Boolean);
  const channels = CHANNELS_BY_INDUSTRY[industry] || CHANNELS_BY_INDUSTRY.ecommerce;
  const hasResults = ontology || compliance || meeting;

  return (
    <div className="space-y-6">

      {/* ── 평시 모니터링 현황 ── */}
      <div className="bg-zinc-900 rounded-2xl border border-zinc-800 px-6 py-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2 flex-shrink-0">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-50" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" />
            </span>
            <span className="text-xs font-bold text-emerald-400 uppercase tracking-widest">{t('risk.live')}</span>
            <span className="text-xs text-zinc-600">{t('risk.last24h')}</span>
          </div>
          <span className="text-xs text-zinc-600">{t('risk.lastScan')}</span>
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-zinc-800/60 rounded-xl px-4 py-3 border border-zinc-700/60">
            <p className="text-xl font-bold text-white leading-none">
              15,402
              {t('risk.count') && <span className="text-xs font-normal text-zinc-400 ml-1">{t('risk.count')}</span>}
            </p>
            <p className="text-xs text-zinc-500 mt-1">{t('risk.analyzedContent')}</p>
            <p className="text-[11px] text-emerald-500 mt-0.5">{t('risk.contentGrowth')}</p>
          </div>
          <div className="bg-emerald-950/40 rounded-xl px-4 py-3 border border-emerald-900/60">
            <p className="text-xl font-bold text-emerald-400 leading-none">
              0
              {t('risk.count') && <span className="text-xs font-normal text-zinc-400 ml-1">{t('risk.count')}</span>}
            </p>
            <p className="text-xs text-zinc-500 mt-1">{t('risk.detectedRisk')}</p>
            <p className="text-[11px] text-emerald-500 mt-0.5">{t('risk.safeState')}</p>
          </div>
          <div className="bg-zinc-800/60 rounded-xl px-4 py-3 border border-zinc-700/60">
            <p className="text-xl font-bold text-white leading-none">
              99.97
              <span className="text-xs font-normal text-zinc-400 ml-1">{t('risk.pct')}</span>
            </p>
            <p className="text-xs text-zinc-500 mt-1">{t('risk.uptime')}</p>
            <p className="text-[11px] text-zinc-500 mt-0.5">{t('risk.noIncident')}</p>
          </div>
        </div>
      </div>

      {/* Header Card */}
      <div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-6">
        <div className="flex items-start justify-between mb-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-zinc-800 border border-zinc-700 rounded-xl flex items-center justify-center">
              <Shield className="text-zinc-400" size={20} />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Risk Intelligence</h2>
              <p className="text-sm text-zinc-500">{t('risk.subtitle')}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            {/* 담당자 공유 드롭다운 */}
            <div className="relative">
              {shareDropdown && (
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setShareDropdown(false)}
                />
              )}
              <button
                onClick={() => setShareDropdown((v) => !v)}
                className="px-3 py-2 bg-zinc-800 text-zinc-300 rounded-xl font-medium hover:bg-zinc-700 transition-colors text-sm flex items-center gap-1.5 border border-zinc-700"
              >
                <Share2 size={14} />{t('risk.shareBtn')}
                <span className="text-zinc-500 text-[10px]">▾</span>
              </button>
              {shareDropdown && (
                <div className="absolute right-0 top-full mt-1 w-52 bg-zinc-800 border border-zinc-700 rounded-xl shadow-xl z-20 overflow-hidden">
                  {SHARE_TARGETS.map((target) => (
                    <button
                      key={target.id}
                      onClick={() => handleShare(target)}
                      className="w-full text-left px-4 py-2.5 text-sm text-zinc-300 hover:bg-zinc-700 hover:text-white transition-colors"
                    >
                      {t(target.labelKey)}
                    </button>
                  ))}
                </div>
              )}
              {shareToast && (
                <div className="absolute -bottom-10 right-0 bg-zinc-700 text-white text-xs px-3 py-1.5 rounded-lg whitespace-nowrap z-30 shadow border border-zinc-600">
                  {shareToast}
                </div>
              )}
            </div>
            <button
              onClick={handleDownload}
              className="px-3 py-2 bg-zinc-800 text-zinc-300 rounded-xl font-medium hover:bg-zinc-700 transition-colors text-sm flex items-center gap-1.5 border border-zinc-700"
            >
              <Download size={14} />{t('risk.downloadBtn')}
            </button>
            {analysisResult && (
              <button
                onClick={runAll}
                disabled={isAnyLoading}
                className="px-3 py-2 bg-purple-600 text-white rounded-xl font-medium hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors text-sm"
              >
                {loading.all ? <><Loader2 className="animate-spin" size={15} />{t('risk.analyzing')}</> : t('risk.runAllBtn')}
              </button>
            )}
          </div>
        </div>

        {/* 브랜드 + 상품명 입력 */}
        <div className="mb-5">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-zinc-500 uppercase tracking-wide mb-2">
            <Search size={12} />{t('risk.registerTarget')}
          </div>
          <div className="flex gap-2">
            <div className="flex flex-col gap-1 w-44 flex-shrink-0">
              <label className="text-[11px] text-zinc-500 font-medium">
                {t(INDUSTRY_INPUT_CFG[industry]?.labelKey1 ?? 'risk.label1_ecommerce')}
              </label>
              <input
                ref={inputRef}
                type="text"
                value={brandName}
                onChange={(e) => setBrandName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !isAnyLoading && handleDemo()}
                readOnly
                className="bg-zinc-800 border border-zinc-700 rounded-xl px-3 py-2.5 text-sm text-white placeholder-zinc-600 focus:outline-none cursor-default transition-colors"
              />
            </div>
            <div className="flex flex-col gap-1 flex-1">
              <label className="text-[11px] text-zinc-500 font-medium">
                {t(INDUSTRY_INPUT_CFG[industry]?.labelKey2 ?? 'risk.label2_ecommerce')}
              </label>
              <input
                type="text"
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !isAnyLoading && handleDemo()}
                readOnly
                className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-3 py-2.5 text-sm text-white placeholder-zinc-600 focus:outline-none cursor-default transition-colors"
              />
            </div>
            <div className="flex flex-col gap-1 flex-shrink-0">
              <span className="text-[11px] text-transparent font-medium select-none">btn</span>
              <button
                onClick={handleDemo}
                disabled={isAnyLoading || (!brandName.trim() && !productName.trim())}
                className="px-5 py-2.5 bg-red-600 text-white rounded-xl font-semibold hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors text-sm h-[42px]"
              >
                {(scanPhase || loading.demo)
                  ? <><Loader2 className="animate-spin" size={15} />{t('risk.scanning')}</>
                  : <><Zap size={15} />{t('risk.analyzeBtn')}</>}
              </button>
            </div>
          </div>
          <p className="mt-2 text-xs text-zinc-600">{t('risk.registerHint')}</p>
        </div>

        {/* Industry + Channels */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div>
            <div className="flex items-center gap-1.5 text-xs font-semibold text-zinc-500 uppercase tracking-wide mb-2">
              <Building2 size={12} />{t('risk.industryContext')}
            </div>
            <div className="flex gap-2 flex-wrap">
              {INDUSTRIES.map(({ id, labelKey, icon }) => (
                <button key={id} onClick={() => {
                  setIndustry(id);
                  const cfg = INDUSTRY_INPUT_CFG[id];
                  setBrandName(cfg.default1);
                  setProductName(cfg.default2);
                  setSelectedExtra(new Set());
                }}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors border ${
                    industry === id
                      ? 'bg-indigo-950 text-indigo-300 border-indigo-700'
                      : 'bg-zinc-800 text-zinc-400 border-zinc-700 hover:bg-zinc-700 hover:text-zinc-300'
                  }`}>
                  {icon} {t(labelKey)}
                </button>
              ))}
            </div>
          </div>
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-zinc-500 uppercase tracking-wide">
                <Radio size={12} />{t('risk.monitoringChannels')}
              </div>
              <span className="text-[11px] text-zinc-600">
                {4 + selectedExtra.size} / 9
              </span>
            </div>
            {/* 기본 4채널 */}
            <div className="flex gap-2 flex-wrap mb-2">
              {channels.map((ch) => (
                <div key={ch.nameKey} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border ${
                  ch.status === 'active'
                    ? 'bg-emerald-950/50 text-emerald-400 border-emerald-900'
                    : 'bg-zinc-800 text-zinc-500 border-zinc-700'
                }`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${ch.status === 'active' ? 'bg-emerald-400' : 'bg-zinc-600'}`} />
                  {t(ch.nameKey)}
                  {ch.count != null && <span className="font-semibold">{ch.count.toLocaleString()}</span>}
                </div>
              ))}
            </div>
            {/* 추가 선택채널 (최대 5) */}
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-[11px] text-zinc-600 mr-0.5">{t('risk.extraChannels')}:</span>
              {(EXTRA_CHANNELS_BY_INDUSTRY[industry] || EXTRA_CHANNELS_BY_INDUSTRY.ecommerce).map(({ id, nameKey }) => {
                const on = selectedExtra.has(id);
                return (
                  <button
                    key={id}
                    onClick={() => toggleExtra(id)}
                    className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs border transition-colors ${
                      on
                        ? 'bg-indigo-950/60 text-indigo-300 border-indigo-700'
                        : 'bg-zinc-800/60 text-zinc-600 border-zinc-700/60 hover:text-zinc-400 hover:border-zinc-600'
                    }`}
                  >
                    {on ? '✓' : '+'} {t(nameKey)}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Error */}
      {errors.demo && (
        <div className="bg-red-950 border border-red-800 text-red-400 rounded-xl px-4 py-3 text-sm">{errors.demo}</div>
      )}

      {/* 스캔 애니메이션 */}
      {scanPhase && (
        <div className="bg-zinc-900 rounded-2xl border border-indigo-900 p-6 flex items-center gap-4">
          <div className="w-10 h-10 bg-indigo-950 border border-indigo-800 rounded-xl flex items-center justify-center flex-shrink-0">
            <ScanSearch className="text-indigo-400 animate-pulse" size={20} />
          </div>
          <div>
            <p className="text-sm font-semibold text-white">{t('risk.scanPhaseTitle')}</p>
            <p className="text-xs text-zinc-500 mt-0.5">
              <span className="text-indigo-400 font-medium">
                {[brandName, productName].filter(Boolean).join(' ')}
              </span>
              {t('risk.scanPhaseHint')}
            </p>
          </div>
          <div className="ml-auto flex gap-1">
            {[0, 1, 2, 3].map((i) => (
              <div
                key={i}
                className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce"
                style={{ animationDelay: `${i * 0.15}s` }}
              />
            ))}
          </div>
        </div>
      )}

      {/* Risk Level Banner */}
      <RiskLevelBanner level={riskLevel} />

      {/* Mock Scenario Cards */}
      {demoResult && <MockScenario data={demoResult} />}

      {/* 전체 로딩 스피너 */}
      {(loading.demo || loading.all) && (
        <RiskLoadingSpinner mode={loading.demo ? 'demo' : 'all'} />
      )}

      {/* Empty State */}
      {!isAnyLoading && !hasResults && !demoResult && (
        <div className="bg-zinc-900 rounded-2xl border border-dashed border-zinc-700 p-12 text-center">
          <Shield className="text-zinc-700 mx-auto mb-3" size={44} />
          <p className="text-zinc-500 text-sm leading-relaxed">
            <span className="font-semibold text-red-400 cursor-pointer hover:text-red-300" onClick={handleDemo}>
              {t('risk.emptyDemo')}
            </span>
            {t('risk.emptyDemoSuffix')}
            {analysisResult && <><br />{t('risk.emptyAllSuffix')}</>}
          </p>
        </div>
      )}

      {/* Ontology Graph */}
      {(hasResults || loading.ontology) && !loading.demo && !loading.all && (
        <OntologyGraph
          data={ontology}
          loading={loading.ontology}
          error={errors.ontology}
          onGenerate={() => runSingle('ontology')}
        />
      )}

      {/* Compliance + Meeting */}
      {(compliance || meeting || loading.compliance || loading.meeting) && !loading.demo && !loading.all && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ComplianceReport
            data={compliance}
            loading={loading.compliance}
            error={errors.compliance}
            onGenerate={() => runSingle('compliance')}
          />
          <MeetingAgenda
            data={meeting}
            loading={loading.meeting}
            error={errors.meeting}
            onGenerate={() => runSingle('meeting')}
          />
        </div>
      )}
    </div>
  );
}
