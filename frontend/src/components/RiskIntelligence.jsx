import { useState } from 'react';
import { Shield, Loader2, Radio, Building2, Zap } from 'lucide-react';
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
  GREEN: { label: '안전', bg: 'bg-green-500', text: 'text-green-700', banner: 'bg-green-50 border-green-200' },
  YELLOW: { label: '주의', bg: 'bg-yellow-400', text: 'text-yellow-700', banner: 'bg-yellow-50 border-yellow-200' },
  ORANGE: { label: '경고', bg: 'bg-orange-500', text: 'text-orange-700', banner: 'bg-orange-50 border-orange-200' },
  RED: { label: '치명적', bg: 'bg-red-600', text: 'text-red-700', banner: 'bg-red-50 border-red-300' },
};

function RiskLevelBanner({ level }) {
  if (!level) return null;
  const cfg = RISK_LEVEL_CONFIG[level] || RISK_LEVEL_CONFIG.GREEN;
  return (
    <div className={`flex items-center gap-3 px-4 py-3 rounded-xl border-2 ${cfg.banner} mb-4`}>
      <span className={`w-3 h-3 rounded-full flex-shrink-0 ${cfg.bg} ${level === 'RED' || level === 'ORANGE' ? 'animate-pulse' : ''}`} />
      <span className={`text-sm font-bold ${cfg.text}`}>
        현재 리스크 등급: {cfg.label}
        {level === 'RED' && ' — 즉각 경영진 대응 필요'}
        {level === 'ORANGE' && ' — 모니터링 강화 필요'}
      </span>
      <span className={`ml-auto text-xs font-bold px-3 py-1 rounded-full text-white ${cfg.bg}`}>
        {cfg.label}
      </span>
    </div>
  );
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

  const analysisData = {
    top_issues: analysisResult?.top_issues || [],
    emerging_issues: analysisResult?.emerging_issues || [],
    recommendations: analysisResult?.recommendations || [],
    all_categories: analysisResult?.all_categories || {},
    stats: analysisResult?.stats || {},
    industry,
  };

  const handleDemo = async () => {
    setLoading((prev) => ({ ...prev, demo: true }));
    setErrors({});
    setDemoResult(null);
    setOntology(null);
    setCompliance(null);
    setMeeting(null);
    setRiskLevel(null);
    try {
      const res = await runDemoScenario();
      const data = res.data;
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

  const reviewCount = analysisResult?.stats?.total_reviews || 0;
  const isAnyLoading = Object.values(loading).some(Boolean);
  const channels = CHANNELS.map((ch) =>
    ch.name === '이커머스 리뷰' ? { ...ch, count: reviewCount } : ch
  );
  const hasResults = ontology || compliance || meeting;

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-start justify-between mb-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 rounded-xl flex items-center justify-center">
              <Shield className="text-purple-600" size={22} />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900">Risk Intelligence</h2>
              <p className="text-sm text-gray-500">
                멀티채널 리스크 모니터링 · 온톨로지 분석 · 컴플라이언스 보고서 · 회의 안건
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              onClick={handleDemo}
              disabled={isAnyLoading}
              className="px-4 py-2.5 bg-red-600 text-white rounded-xl font-medium hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors text-sm"
            >
              {loading.demo ? (
                <><Loader2 className="animate-spin" size={15} />분석 중...</>
              ) : (
                <><Zap size={15} />충전기 폭발 사건 시연</>
              )}
            </button>
            {analysisResult && (
              <button
                onClick={runAll}
                disabled={isAnyLoading}
                className="px-4 py-2.5 bg-purple-600 text-white rounded-xl font-medium hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors text-sm"
              >
                {loading.all ? (
                  <><Loader2 className="animate-spin" size={15} />분석 중...</>
                ) : '전체 분석 실행'}
              </button>
            )}
          </div>
        </div>

        {/* Industry + Channels */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div>
            <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-500 mb-2">
              <Building2 size={13} />산업 컨텍스트
            </div>
            <div className="flex gap-2 flex-wrap">
              {INDUSTRIES.map(({ id, label, icon }) => (
                <button key={id} onClick={() => setIndustry(id)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    industry === id ? 'bg-purple-100 text-purple-700 ring-1 ring-purple-300' : 'bg-gray-50 text-gray-500 hover:bg-gray-100'
                  }`}>
                  {icon} {label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-500 mb-2">
              <Radio size={13} />모니터링 채널
            </div>
            <div className="flex gap-2 flex-wrap">
              {channels.map((ch) => (
                <div key={ch.name} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs ${
                  ch.status === 'active' ? 'bg-green-50 text-green-700' : 'bg-gray-50 text-gray-400'
                }`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${ch.status === 'active' ? 'bg-green-500' : 'bg-gray-300'}`} />
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
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm">{errors.demo}</div>
      )}

      {/* Risk Level Banner */}
      <RiskLevelBanner level={riskLevel} />

      {/* Mock Scenario Cards */}
      {demoResult && <MockScenario data={demoResult} />}

      {/* Empty State */}
      {!isAnyLoading && !hasResults && !demoResult && (
        <div className="bg-white rounded-2xl border border-dashed border-gray-200 p-12 text-center">
          <Shield className="text-gray-200 mx-auto mb-3" size={48} />
          <p className="text-gray-400 text-sm leading-relaxed">
            <span className="font-semibold text-red-500 cursor-pointer hover:underline" onClick={handleDemo}>
              ⚡ 충전기 폭발 사건 시연
            </span>
            으로 4채널 동시 감지 → Red Alert 시나리오를 즉시 확인하세요.
            {analysisResult && <><br />또는 업로드된 데이터로 <span className="text-purple-600 font-semibold">전체 분석 실행</span>을 눌러보세요.</>}
          </p>
        </div>
      )}

      {/* Ontology Graph */}
      {(hasResults || isAnyLoading) && (
        <OntologyGraph
          data={ontology}
          loading={loading.all || loading.ontology || loading.demo}
          error={errors.ontology}
          onGenerate={() => runSingle('ontology')}
        />
      )}

      {/* Compliance + Meeting */}
      {(compliance || meeting || loading.all || loading.demo || loading.compliance || loading.meeting) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ComplianceReport
            data={compliance}
            loading={loading.all || loading.compliance || loading.demo}
            error={errors.compliance}
            onGenerate={() => runSingle('compliance')}
          />
          <MeetingAgenda
            data={meeting}
            loading={loading.all || loading.meeting || loading.demo}
            error={errors.meeting}
            onGenerate={() => runSingle('meeting')}
          />
        </div>
      )}
    </div>
  );
}
