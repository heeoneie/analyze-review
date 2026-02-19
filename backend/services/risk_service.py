"""
리스크 인텔리전스 서비스
온톨로지 그래프, 컴플라이언스 보고서, 회의 안건 자동 생성
"""

import json
import logging

from core.utils.json_utils import extract_json_from_text
from core.utils.openai_client import call_openai_json, get_client

logger = logging.getLogger(__name__)

RISK_SYSTEM_PROMPT = (
    "You are an enterprise risk intelligence analyst specializing in "
    "e-commerce reputation monitoring and compliance reporting. "
    "Always respond in Korean with valid JSON."
)


def generate_ontology(analysis_data: dict) -> dict:
    """분석 결과를 기반으로 온톨로지 지식 그래프 생성"""
    prompt = f"""다음 이커머스 리뷰 분석 결과를 기반으로 리스크 온톨로지 지식 그래프를 생성하세요.

## 분석 데이터
- 주요 이슈: {json.dumps(analysis_data.get('top_issues', []), ensure_ascii=False)}
- 급증 이슈: {json.dumps(analysis_data.get('emerging_issues', []), ensure_ascii=False)}
- 개선 권고: {json.dumps(analysis_data.get('recommendations', []), ensure_ascii=False)}
- 전체 카테고리: {json.dumps(analysis_data.get('all_categories', {}), ensure_ascii=False)}

## 출력 형식
다음 JSON 형식으로 노드와 링크를 생성하세요:

{{
  "nodes": [
    {{"id": "node_1", "label": "배송 지연", "type": "category", "severity": 8}},
    {{"id": "node_2", "label": "물류 센터 과부하", "type": "root_cause", "severity": 6}},
    {{"id": "node_3", "label": "물류팀", "type": "department", "severity": 5}},
    {{"id": "node_4", "label": "집단 보이콧", "type": "risk_type", "severity": 9}}
  ],
  "links": [
    {{"source": "node_1", "target": "node_2", "relation": "원인"}},
    {{"source": "node_2", "target": "node_3", "relation": "담당"}},
    {{"source": "node_1", "target": "node_4", "relation": "리스크_유발"}}
  ],
  "summary": "전체 리스크 그래프 요약 (2-3문장)"
}}

## 규칙
1. 노드 유형 4가지: category(이슈 카테고리), root_cause(근본 원인), department(담당 부서), risk_type(리스크 유형)
2. 리스크 유형 종류: 법적 분쟁, 집단 보이콧, 안전 사고, 내부 폭로, 평판 하락, 매출 감소, 고객 이탈
3. 링크 관계: 원인, 담당, 리스크_유발, 대응_필요, 영향
4. 노드 15~25개 생성, severity는 1-10 스케일
5. 분석 데이터의 실제 이슈를 반영하여 현실적인 인과관계를 구성하세요"""

    client = get_client()
    content = call_openai_json(client, prompt, system_prompt=RISK_SYSTEM_PROMPT)
    result = extract_json_from_text(content)

    if not result or "nodes" not in result:
        return {"nodes": [], "links": [], "summary": "온톨로지 생성에 실패했습니다."}
    return result


def generate_compliance_report(analysis_data: dict) -> dict:
    """분석 결과를 기반으로 컴플라이언스 모니터링 보고서 생성"""
    stats = analysis_data.get("stats", {})
    prompt = f"""다음 이커머스 리뷰 분석 결과를 기반으로 컴플라이언스 모니터링 보고서를 생성하세요.

## 분석 데이터
- 통계: {json.dumps(stats, ensure_ascii=False)}
- 주요 이슈: {json.dumps(analysis_data.get('top_issues', []), ensure_ascii=False)}
- 급증 이슈: {json.dumps(analysis_data.get('emerging_issues', []), ensure_ascii=False)}
- 개선 권고: {json.dumps(analysis_data.get('recommendations', []), ensure_ascii=False)}

## 출력 형식
{{
  "report_title": "리뷰 리스크 모니터링 보고서",
  "report_date": "2025-02-19",
  "overall_risk_level": "주의",
  "monitoring_summary": "최근 24시간 동안 1개 채널에서 총 N건의 리뷰를 모니터링한 결과, 부정 리뷰 M건이 감지되었습니다. 주요 리스크 영역은 ...",
  "risk_assessment": {{
    "legal": {{"level": "low", "description": "법적 리스크 설명"}},
    "reputation": {{"level": "medium", "description": "평판 리스크 설명"}},
    "operational": {{"level": "high", "description": "운영 리스크 설명"}},
    "safety": {{"level": "low", "description": "안전 리스크 설명"}}
  }},
  "risk_events": [
    {{
      "id": 1,
      "severity": "high",
      "category": "이슈 카테고리",
      "description": "감지된 리스크 이벤트 설명",
      "affected_count": 15,
      "recommended_action": "권장 대응 조치"
    }}
  ],
  "next_actions": [
    "즉시 조치가 필요한 항목 1",
    "모니터링 강화가 필요한 항목 2"
  ]
}}

## 규칙
1. overall_risk_level: 안전/주의/경고/위험 중 하나
2. risk_assessment 각 항목의 level: low/medium/high
3. 실제 분석 데이터의 수치를 반영하세요
4. risk_events는 심각도 순으로 최대 5개
5. 공식적이고 전문적인 어조로 작성하세요"""

    client = get_client()
    content = call_openai_json(client, prompt, system_prompt=RISK_SYSTEM_PROMPT)
    result = extract_json_from_text(content)

    if not result:
        return {
            "report_title": "보고서 생성 실패",
            "overall_risk_level": "알 수 없음",
            "monitoring_summary": "보고서 생성에 실패했습니다.",
            "risk_assessment": {},
            "risk_events": [],
            "next_actions": [],
        }
    return result


def generate_meeting_agenda(analysis_data: dict) -> dict:
    """분석 결과를 기반으로 긴급 회의 안건 자동 생성"""
    prompt = f"""다음 이커머스 리뷰 분석 결과를 기반으로 긴급 품질 개선 회의 안건을 생성하세요.

## 분석 데이터
- 주요 이슈: {json.dumps(analysis_data.get('top_issues', []), ensure_ascii=False)}
- 급증 이슈: {json.dumps(analysis_data.get('emerging_issues', []), ensure_ascii=False)}
- 개선 권고: {json.dumps(analysis_data.get('recommendations', []), ensure_ascii=False)}
- 통계: {json.dumps(analysis_data.get('stats', {}), ensure_ascii=False)}

## 출력 형식
{{
  "meeting_title": "긴급 고객 리뷰 리스크 대응 회의",
  "urgency": "긴급",
  "estimated_duration": "60분",
  "attendees": [
    {{"department": "CS팀", "role": "팀장", "reason": "고객 불만 대응 총괄"}},
    {{"department": "물류팀", "role": "매니저", "reason": "배송 관련 이슈 책임자"}}
  ],
  "agenda_items": [
    {{
      "order": 1,
      "title": "급증 이슈 현황 보고",
      "priority": "critical",
      "duration": "15분",
      "presenter": "데이터분석팀",
      "discussion_points": [
        "최근 30일 부정 리뷰 급증 현황",
        "주요 이슈 카테고리별 분포"
      ],
      "action_items": [
        {{
          "task": "구체적인 조치 사항",
          "owner": "담당 부서/역할",
          "deadline": "D+3"
        }}
      ]
    }}
  ],
  "preparation": [
    "사전에 준비할 자료 1",
    "사전에 검토할 데이터 2"
  ]
}}

## 규칙
1. urgency: 일반/긴급/초긴급 중 하나 (급증 이슈가 있으면 긴급 이상)
2. priority: critical/high/medium/low
3. 급증 이슈가 있으면 반드시 첫 번째 안건으로 배치
4. attendees에 부서별 참석 사유를 명확히
5. action_items에 구체적인 담당자와 기한 포함
6. agenda_items는 3~5개로 구성"""

    client = get_client()
    content = call_openai_json(client, prompt, system_prompt=RISK_SYSTEM_PROMPT)
    result = extract_json_from_text(content)

    if not result:
        return {
            "meeting_title": "회의 안건 생성 실패",
            "urgency": "알 수 없음",
            "attendees": [],
            "agenda_items": [],
            "preparation": [],
        }
    return result
