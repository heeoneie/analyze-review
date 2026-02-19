import { useState } from 'react';
import { Shield, Loader2 } from 'lucide-react';
import {
  generateOntology,
  generateComplianceReport,
  generateMeetingAgenda,
} from '../api/client';
import OntologyGraph from './OntologyGraph';
import ComplianceReport from './ComplianceReport';
import MeetingAgenda from './MeetingAgenda';

export default function RiskIntelligence({ analysisResult }) {
  const [ontology, setOntology] = useState(null);
  const [compliance, setCompliance] = useState(null);
  const [meeting, setMeeting] = useState(null);
  const [loading, setLoading] = useState({ all: false, ontology: false, compliance: false, meeting: false });
  const [errors, setErrors] = useState({});

  const analysisData = {
    top_issues: analysisResult?.top_issues || [],
    emerging_issues: analysisResult?.emerging_issues || [],
    recommendations: analysisResult?.recommendations || [],
    all_categories: analysisResult?.all_categories || {},
    stats: analysisResult?.stats || {},
  };

  const runAll = async () => {
    setLoading((prev) => ({ ...prev, all: true }));
    setErrors({});
    try {
      const [ontRes, compRes, meetRes] = await Promise.allSettled([
        generateOntology(analysisData),
        generateComplianceReport(analysisData),
        generateMeetingAgenda(analysisData),
      ]);
      if (ontRes.status === 'fulfilled') setOntology(ontRes.value.data);
      else setErrors((prev) => ({ ...prev, ontology: '온톨로지 생성 실패' }));
      if (compRes.status === 'fulfilled') setCompliance(compRes.value.data);
      else setErrors((prev) => ({ ...prev, compliance: '보고서 생성 실패' }));
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
      if (type === 'ontology') {
        const res = await generateOntology(analysisData);
        setOntology(res.data);
      } else if (type === 'compliance') {
        const res = await generateComplianceReport(analysisData);
        setCompliance(res.data);
      } else if (type === 'meeting') {
        const res = await generateMeetingAgenda(analysisData);
        setMeeting(res.data);
      }
    } catch {
      setErrors((prev) => ({ ...prev, [type]: `${type} 생성 실패` }));
    } finally {
      setLoading((prev) => ({ ...prev, [type]: false }));
    }
  };

  const isAnyLoading = loading.all || loading.ontology || loading.compliance || loading.meeting;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 rounded-xl flex items-center justify-center">
              <Shield className="text-purple-600" size={22} />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900">Risk Intelligence</h2>
              <p className="text-sm text-gray-500">
                AI 기반 리스크 온톨로지 분석 · 컴플라이언스 보고서 · 회의 안건 자동 생성
              </p>
            </div>
          </div>
          <button
            onClick={runAll}
            disabled={isAnyLoading}
            className="px-5 py-2.5 bg-purple-600 text-white rounded-xl font-medium hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
          >
            {loading.all ? (
              <>
                <Loader2 className="animate-spin" size={16} />
                분석 중...
              </>
            ) : (
              '전체 리스크 분석 실행'
            )}
          </button>
        </div>
      </div>

      {/* Ontology Graph - Full Width */}
      <OntologyGraph
        data={ontology}
        loading={loading.all || loading.ontology}
        error={errors.ontology}
        onGenerate={() => runSingle('ontology')}
      />

      {/* Compliance Report + Meeting Agenda - 2 Columns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ComplianceReport
          data={compliance}
          loading={loading.all || loading.compliance}
          error={errors.compliance}
          onGenerate={() => runSingle('compliance')}
        />
        <MeetingAgenda
          data={meeting}
          loading={loading.all || loading.meeting}
          error={errors.meeting}
          onGenerate={() => runSingle('meeting')}
        />
      </div>
    </div>
  );
}
