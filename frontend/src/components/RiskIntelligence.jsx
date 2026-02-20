import { useState, useRef } from 'react';
import { Shield, Loader2, Radio, Building2, Zap, Share2, Download, Search, ScanSearch } from 'lucide-react';
import {
  generateOntology,
  generateComplianceReport,
  generateMeetingAgenda,
  runDemoScenario,
} from '../api/client';
import OntologyGraph from './OntologyGraph';
import ComplianceReport from './ComplianceReport';
import MeetingAgenda from './MeetingAgenda';
import MockScenario from './MockScenario';
import RiskLoadingSpinner from './RiskLoadingSpinner';

const INDUSTRIES = [
  { id: 'ecommerce', label: '이커머스', icon: '🛒' },
  { id: 'hospital', label: '병원·의료', icon: '🏥' },
  { id: 'finance', label: '금융·핀테크', icon: '🏦' },
  { id: 'gaming', label: '게임·엔터', icon: '🎮' },
];

const CHANNELS = [
  { name: '이커머스 리뷰', status: 'active' },
  { name: '네이버 블로그', status: 'ready' },
  { name: 'YouTube 댓글', status: 'ready' },
  { name: '커뮤니티 게시글', status: 'ready' },
];

const RISK_LEVEL_CONFIG = {
  GREEN:  { label: '안전',   dot: 'bg-emerald-400', text: 'text-emerald-400', banner: 'bg-emerald-950/40 border-emerald-800' },
  YELLOW: { label: '주의',   dot: 'bg-amber-400',   text: 'text-amber-400',   banner: 'bg-amber-950/40 border-amber-800' },
  ORANGE: { label: '경고',   dot: 'bg-orange-400',  text: 'text-orange-400',  banner: 'bg-orange-950/40 border-orange-800' },
  RED:    { label: '치명적', dot: 'bg-red-500',     text: 'text-red-400',     banner: 'bg-red-950/40 border-red-800' },
};

function RiskLevelBanner({ level }) {
  if (!level) return null;
  const cfg = RISK_LEVEL_CONFIG[level] || RISK_LEVEL_CONFIG.GREEN;
  return (
    <div className={`flex items-center gap-3 px-4 py-3 rounded-xl border ${cfg.banner}`}>
      <span className={`relative flex h-3 w-3 flex-shrink-0`}>
        {(level === 'RED' || level === 'ORANGE') && (
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${cfg.dot} opacity-50`} />
        )}
        <span className={`relative inline-flex rounded-full h-3 w-3 ${cfg.dot}`} />
      </span>
      <span className={`text-sm font-semibold ${cfg.text}`}>
        현재 리스크 등급: {cfg.label}
        {level === 'RED' && ' — 즉각 경영진 대응 필요'}
        {level === 'ORANGE' && ' — 모니터링 강화 필요'}
      </span>
      <span className={`ml-auto text-xs font-bold px-3 py-1 rounded-full border ${cfg.banner} ${cfg.text}`}>
        {cfg.label}
      </span>
    </div>
  );
}

// "OO" 플레이스홀더를 브랜드명으로 교체 (deep replace)
function injectBrand(obj, brand) {
  if (!brand || !obj) return obj;
  return JSON.parse(JSON.stringify(obj).replace(/OO/g, brand));
}

export default function RiskIntelligence({ analysisResult }) {
  const [demoResult, setDemoResult] = useState(null);
  const [ontology, setOntology] = useState(null);
  const [compliance, setCompliance] = useState(null);
  const [meeting, setMeeting] = useState(null);
  const [riskLevel, setRiskLevel] = useState(null);
  const [loading, setLoading] = useState({ demo: false, all: false, ontology: false, compliance: false, meeting: false });
  const [errors, setErrors] = useState({});
  const [industry, setIndustry] = useState('ecommerce');
  const [shareToast, setShareToast] = useState(false);
  const [brandName, setBrandName] = useState('넥서스');
  const [productName, setProductName] = useState('파워 충전기 65W');
  const [scanPhase, setScanPhase] = useState(false);
  const inputRef = useRef(null);

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

    // 1단계: 스캔 애니메이션 (1.5초)
    setScanPhase(true);
    setErrors({});
    setDemoResult(null);
    setOntology(null);
    setCompliance(null);
    setMeeting(null);
    setRiskLevel(null);
    await new Promise((r) => setTimeout(r, 1500));
    setScanPhase(false);

    // 2단계: API 호출
    setLoading((prev) => ({ ...prev, demo: true }));
    try {
      const res = await runDemoScenario();
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

  const handleShare = async () => {
    await navigator.clipboard.writeText(window.location.href);
    setShareToast(true);
    setTimeout(() => setShareToast(false), 2000);
  };

  const handleDownload = () => {
    const now = new Date().toLocaleString('ko-KR');
    const lines = [
      '═══════════════════════════════════════════════════',
      'OntoReview — AI Risk Intelligence Report',
      '═══════════════════════════════════════════════════',
      `생성일시: ${now}`,
      '',
    ];

    if (demoResult) {
      lines.push(`[사건명] ${demoResult.incident_title}`);
      lines.push(`[위험등급] ${riskLevel}`);
      lines.push(`[사건 요약] ${demoResult.incident_summary}`);
      if (demoResult.clustering_reason) {
        lines.push(`[클러스터링] ${demoResult.clustering_reason}`);
      }
      lines.push('');
      lines.push('── 감지된 채널 신호 ──');
      demoResult.channel_signals?.forEach((s, i) => {
        lines.push(`\n[${i + 1}] ${s.platform} (${s.data_type})`);
        lines.push(`내용: ${s.content}`);
        lines.push(`리스크: ${s.risk_indicators?.join(', ')}`);
        if (s.viral_risk) lines.push(`역바이럴 가능성: ${s.viral_risk}`);
      });
      lines.push('');
    }

    if (compliance) {
      lines.push('── 컴플라이언스 보고서 ──');
      lines.push(`전체 리스크 레벨: ${compliance.overall_risk_level}`);
      lines.push(`모니터링 요약: ${compliance.monitoring_summary}`);
      lines.push('');
      if (compliance.next_actions?.length) {
        lines.push('다음 조치사항:');
        compliance.next_actions.forEach((a, i) => lines.push(`  ${i + 1}. ${a}`));
        lines.push('');
      }
    }

    if (meeting) {
      lines.push('── 긴급 회의 안건 ──');
      lines.push(`회의명: ${meeting.meeting_title}`);
      lines.push(`긴급도: ${meeting.urgency} / 예상 시간: ${meeting.estimated_duration}`);
      lines.push('');
      meeting.agenda_items?.forEach((item, i) => {
        lines.push(`  [${i + 1}] ${item.title} (${item.priority}) — ${item.duration}`);
      });
      lines.push('');
    }

    lines.push('─────────────────────────────────────────────────');
    lines.push('Generated by OntoReview — AI Reputation Intelligence');

    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `risk-report-${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const reviewCount = analysisResult?.stats?.total_reviews || 0;
  const isAnyLoading = Object.values(loading).some(Boolean);
  const channels = CHANNELS.map((ch) =>
    ch.name === '이커머스 리뷰' ? { ...ch, count: reviewCount } : ch
  );
  const hasResults = ontology || compliance || meeting;

  return (
    <div className="space-y-6">
      {/* Header Card */}
      {/* Header */}
      <div className="bg-slate-900 rounded-2xl border border-slate-800 p-6">
        <div className="flex items-start justify-between mb-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-slate-800 border border-slate-700 rounded-xl flex items-center justify-center">
              <Shield className="text-slate-400" size={20} />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Risk Intelligence</h2>
              <p className="text-sm text-slate-500">
                멀티채널 리스크 모니터링 · 온톨로지 분석 · 컴플라이언스 보고서 · 회의 안건
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <div className="relative">
              <button
                onClick={handleShare}
                className="px-3 py-2 bg-slate-800 text-slate-300 rounded-xl font-medium hover:bg-slate-700 transition-colors text-sm flex items-center gap-1.5 border border-slate-700"
              >
                <Share2 size={14} />담당자 공유
              </button>
              {shareToast && (
                <div className="absolute -bottom-9 left-1/2 -translate-x-1/2 bg-slate-700 text-white text-xs px-2.5 py-1.5 rounded-lg whitespace-nowrap z-10 shadow border border-slate-600">
                  ✓ 링크 복사됨
                </div>
              )}
            </div>
            <button
              onClick={handleDownload}
              disabled={!hasResults && !demoResult}
              className="px-3 py-2 bg-slate-800 text-slate-300 rounded-xl font-medium hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-sm flex items-center gap-1.5 border border-slate-700"
            >
              <Download size={14} />리포트 다운로드
            </button>
            {analysisResult && (
              <button
                onClick={runAll}
                disabled={isAnyLoading}
                className="px-3 py-2 bg-purple-600 text-white rounded-xl font-medium hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors text-sm"
              >
                {loading.all ? <><Loader2 className="animate-spin" size={15} />분석 중...</> : '전체 분석 실행'}
              </button>
            )}
          </div>
        </div>

        {/* 브랜드 + 상품명 입력 */}
        <div className="mb-5">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
            <Search size={12} />분석 대상 등록
          </div>
          <div className="flex gap-2">
            {/* 브랜드명 */}
            <div className="flex flex-col gap-1 w-44 flex-shrink-0">
              <label className="text-[11px] text-slate-500 font-medium">브랜드명</label>
              <input
                ref={inputRef}
                type="text"
                value={brandName}
                onChange={(e) => setBrandName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !isAnyLoading && handleDemo()}
                placeholder="예: 넥서스"
                className="bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600 transition-colors"
              />
            </div>
            {/* 상품명 */}
            <div className="flex flex-col gap-1 flex-1">
              <label className="text-[11px] text-slate-500 font-medium">상품명</label>
              <input
                type="text"
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !isAnyLoading && handleDemo()}
                placeholder="예: 파워 충전기 65W"
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600 transition-colors"
              />
            </div>
            {/* 분석 버튼 */}
            <div className="flex flex-col gap-1 flex-shrink-0">
              <span className="text-[11px] text-transparent font-medium select-none">버튼</span>
              <button
                onClick={handleDemo}
                disabled={isAnyLoading || (!brandName.trim() && !productName.trim())}
                className="px-5 py-2.5 bg-red-600 text-white rounded-xl font-semibold hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors text-sm h-[42px]"
              >
                {(scanPhase || loading.demo) ? (
                  <><Loader2 className="animate-spin" size={15} />스캔 중...</>
                ) : (
                  <><Zap size={15} />리스크 분석 시작</>
                )}
              </button>
            </div>
          </div>
          <p className="mt-2 text-xs text-slate-600">
            등록된 브랜드·상품을 온톨로지 엔티티로 설정하여 쿠팡·YouTube·네이버·커뮤니티 4채널을 동시 스캔합니다
          </p>
        </div>

        {/* Industry + Channels */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div>
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
              <Building2 size={12} />산업 컨텍스트
            </div>
            <div className="flex gap-2 flex-wrap">
              {INDUSTRIES.map(({ id, label, icon }) => (
                <button key={id} onClick={() => setIndustry(id)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors border ${
                    industry === id
                      ? 'bg-indigo-950 text-indigo-300 border-indigo-700'
                      : 'bg-slate-800 text-slate-400 border-slate-700 hover:bg-slate-700 hover:text-slate-300'
                  }`}>
                  {icon} {label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
              <Radio size={12} />모니터링 채널
            </div>
            <div className="flex gap-2 flex-wrap">
              {channels.map((ch) => (
                <div key={ch.name} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border ${
                  ch.status === 'active'
                    ? 'bg-emerald-950/50 text-emerald-400 border-emerald-900'
                    : 'bg-slate-800 text-slate-500 border-slate-700'
                }`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${ch.status === 'active' ? 'bg-emerald-400' : 'bg-slate-600'}`} />
                  {ch.name}
                  {ch.count != null && <span className="font-semibold">{ch.count.toLocaleString()}</span>}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Error */}
      {errors.demo && (
        <div className="bg-red-950 border border-red-800 text-red-400 rounded-xl px-4 py-3 text-sm">{errors.demo}</div>
      )}

      {/* 스캔 애니메이션 (1.5초) */}
      {scanPhase && (
        <div className="bg-slate-900 rounded-2xl border border-indigo-900 p-6 flex items-center gap-4">
          <div className="w-10 h-10 bg-indigo-950 border border-indigo-800 rounded-xl flex items-center justify-center flex-shrink-0">
            <ScanSearch className="text-indigo-400 animate-pulse" size={20} />
          </div>
          <div>
            <p className="text-sm font-semibold text-white">
              온톨로지 엔진이 24시간 여론 데이터 스캔 중...
            </p>
            <p className="text-xs text-slate-500 mt-0.5">
              <span className="text-indigo-400 font-medium">
                {[brandName, productName].filter(Boolean).join(' ')}
              </span>
              {' '}관련 쿠팡·YouTube·네이버·커뮤니티 신호 감지 중
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

      {/* 전체 로딩 스피너 (demo / runAll 중) */}
      {(loading.demo || loading.all) && (
        <RiskLoadingSpinner mode={loading.demo ? 'demo' : 'all'} />
      )}

      {/* Empty State */}
      {!isAnyLoading && !hasResults && !demoResult && (
        <div className="bg-slate-900 rounded-2xl border border-dashed border-slate-700 p-12 text-center">
          <Shield className="text-slate-700 mx-auto mb-3" size={44} />
          <p className="text-slate-500 text-sm leading-relaxed">
            <span className="font-semibold text-red-400 cursor-pointer hover:text-red-300" onClick={handleDemo}>
              ⚡ 충전기 폭발 사건 시연
            </span>
            으로 4채널 동시 감지 → Red Alert 시나리오를 즉시 확인하세요.
            {analysisResult && <><br />또는 업로드된 데이터로 <span className="text-indigo-400 font-semibold">전체 분석 실행</span>을 눌러보세요.</>}
          </p>
        </div>
      )}

      {/* Ontology Graph — demo/all 로딩 중에는 숨김 (스피너가 대신 표시) */}
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
