"""
리스크 인텔리전스 서비스
온톨로지 그래프, 컴플라이언스 보고서, 회의 안건 자동 생성
산업별 컨텍스트 + 멀티채널 모니터링 지원
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor

from core.utils.json_utils import extract_json_from_text
from core.utils.openai_client import call_openai_json, get_client

logger = logging.getLogger(__name__)

INDUSTRY_CONTEXT = {
    "ecommerce": {
        "name": "이커머스",
        "risks": "배송 지연, 품질 불량, 반품/환불 분쟁, 허위 광고, 개인정보 유출",
        "departments": "CS팀, 물류팀, 품질관리팀, 마케팅팀, 법무팀",
        "channels": "이커머스 리뷰, 네이버 블로그, YouTube, 커뮤니티",
    },
    "hospital": {
        "name": "병원·의료",
        "risks": "의료 사고, 진료비 분쟁, 대기 시간 불만, 의료진 태도, 감염 관리, 개인정보 유출",
        "departments": "진료부, 간호부, 원무팀, QI팀(질 향상), 감염관리팀, 법무팀",
        "channels": "병원 리뷰, 네이버 블로그, 의료 커뮤니티, YouTube, 뉴스",
    },
    "finance": {
        "name": "금융·핀테크",
        "risks": "금융 사기, 시스템 장애, 수수료 불만, 고객 정보 유출, 규제 위반, 투자 손실 분쟁",
        "departments": "리스크관리팀, 컴플라이언스팀, IT보안팀, CS팀, 법무팀",
        "channels": "앱 리뷰, 금융 커뮤니티, 네이버 블로그, YouTube, 뉴스",
    },
    "gaming": {
        "name": "게임·엔터테인먼트",
        "risks": "과금 불만, 버그/서버 장애, 핵/치팅, 확률 조작 의혹, 커뮤니티 독성, 개인정보 유출",
        "departments": "운영팀, QA팀, 개발팀, CS팀, 법무팀, 커뮤니티 매니저",
        "channels": "스토어 리뷰, 게임 커뮤니티, YouTube, 디스코드, 트위치",
    },
}

RISK_SYSTEM_PROMPT = (
    "You are an enterprise risk intelligence analyst specializing in "
    "multi-channel reputation monitoring and compliance reporting. "
    "Always respond in Korean with valid JSON."
)


def _get_industry(analysis_data: dict) -> dict:
    industry_id = analysis_data.get("industry", "ecommerce")
    return INDUSTRY_CONTEXT.get(industry_id, INDUSTRY_CONTEXT["ecommerce"])


def generate_ontology(analysis_data: dict) -> dict:
    """분석 결과를 기반으로 온톨로지 지식 그래프 생성"""
    ind = _get_industry(analysis_data)
    prompt = f"""다음은 {ind['name']} 산업의 멀티채널({ind['channels']}) 고객 피드백 분석 결과입니다.
이 데이터를 기반으로 리스크 온톨로지 지식 그래프를 생성하세요.

## 분석 데이터
- 주요 이슈: {json.dumps(analysis_data.get('top_issues', []), ensure_ascii=False)}
- 급증 이슈: {json.dumps(analysis_data.get('emerging_issues', []), ensure_ascii=False)}
- 개선 권고: {json.dumps(analysis_data.get('recommendations', []), ensure_ascii=False)}
- 전체 카테고리: {json.dumps(analysis_data.get('all_categories', {}), ensure_ascii=False)}

## 산업 컨텍스트
- 산업: {ind['name']}
- 주요 리스크: {ind['risks']}
- 핵심 부서: {ind['departments']}
- 모니터링 채널: {ind['channels']}

## 출력 형식
다음 JSON 형식으로 노드와 링크를 생성하세요:

{{
  "nodes": [
    {{"id": "node_1", "label": "이슈명", "type": "category", "severity": 8}},
    {{"id": "node_2", "label": "근본 원인", "type": "root_cause", "severity": 6}},
    {{"id": "node_3", "label": "담당 부서", "type": "department", "severity": 5}},
    {{"id": "node_4", "label": "리스크 유형", "type": "risk_type", "severity": 9}},
    {{"id": "node_5", "label": "채널명", "type": "channel", "severity": 4}}
  ],
  "links": [
    {{"source": "node_1", "target": "node_2", "relation": "원인"}},
    {{"source": "node_2", "target": "node_3", "relation": "담당"}},
    {{"source": "node_1", "target": "node_4", "relation": "리스크_유발"}},
    {{"source": "node_5", "target": "node_1", "relation": "감지"}}
  ],
  "summary": "전체 리스크 그래프 요약 (2-3문장)"
}}

## 규칙
1. 노드 유형 5가지: category(이슈 카테고리), root_cause(근본 원인), department(담당 부서), risk_type(리스크 유형), channel(감지 채널)
2. 리스크 유형: 법적 분쟁, 집단 보이콧, 안전 사고, 내부 폭로, 평판 하락, 매출 감소, 고객 이탈, 규제 제재
3. 링크 관계: 원인, 담당, 리스크_유발, 대응_필요, 영향, 감지, 확산
4. 노드 15~25개 생성, severity는 1-10 스케일
5. {ind['name']} 산업의 맥락에 맞게 부서명과 리스크를 구체적으로 작성하세요
6. 채널 노드를 포함하여 어디서 이슈가 감지되었는지 표현하세요"""

    client = get_client()
    content = call_openai_json(client, prompt, system_prompt=RISK_SYSTEM_PROMPT)
    result = extract_json_from_text(content)

    if not result or "nodes" not in result:
        return {"nodes": [], "links": [], "summary": "온톨로지 생성에 실패했습니다."}
    return result


def generate_compliance_report(analysis_data: dict) -> dict:
    """분석 결과를 기반으로 컴플라이언스 모니터링 보고서 생성"""
    ind = _get_industry(analysis_data)
    stats = analysis_data.get("stats", {})
    prompt = f"""다음은 {ind['name']} 산업의 멀티채널 모니터링 결과입니다.
컴플라이언스 모니터링 보고서를 생성하세요.

## 분석 데이터
- 통계: {json.dumps(stats, ensure_ascii=False)}
- 주요 이슈: {json.dumps(analysis_data.get('top_issues', []), ensure_ascii=False)}
- 급증 이슈: {json.dumps(analysis_data.get('emerging_issues', []), ensure_ascii=False)}
- 개선 권고: {json.dumps(analysis_data.get('recommendations', []), ensure_ascii=False)}

## 산업 컨텍스트
- 산업: {ind['name']}
- 주요 리스크: {ind['risks']}
- 모니터링 채널: {ind['channels']}

## 출력 형식
{{
  "report_title": "{ind['name']} 리스크 모니터링 보고서",
  "report_date": "2025-02-20",
  "overall_risk_level": "주의",
  "monitoring_summary": "최근 24시간 동안 {ind['channels']} 등 다수 채널에서 총 N건의 고객 피드백을 모니터링한 결과, 부정 피드백 M건이 감지되었습니다. 주요 리스크 영역은 ...",
  "monitored_channels": [
    {{"channel": "채널명", "feed_count": 100, "risk_count": 15, "status": "active"}}
  ],
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
      "channel": "감지 채널",
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
4. risk_events는 심각도 순으로 최대 5개, 각 이벤트에 감지 채널 명시
5. monitored_channels에 각 채널별 모니터링 현황 포함
6. {ind['name']} 산업의 규제 및 컴플라이언스 기준에 맞게 작성하세요
7. 공식적이고 전문적인 어조로 작성하세요"""

    client = get_client()
    content = call_openai_json(client, prompt, system_prompt=RISK_SYSTEM_PROMPT)
    result = extract_json_from_text(content)

    if not result:
        return {
            "report_title": "보고서 생성 실패",
            "overall_risk_level": "알 수 없음",
            "monitoring_summary": "보고서 생성에 실패했습니다.",
            "monitored_channels": [],
            "risk_assessment": {},
            "risk_events": [],
            "next_actions": [],
        }
    return result


def generate_meeting_agenda(analysis_data: dict) -> dict:
    """분석 결과를 기반으로 긴급 회의 안건 자동 생성"""
    ind = _get_industry(analysis_data)
    prompt = f"""다음은 {ind['name']} 산업의 멀티채널 모니터링에서 감지된 리스크 분석 결과입니다.
긴급 리스크 대응 회의 안건을 생성하세요.

## 분석 데이터
- 주요 이슈: {json.dumps(analysis_data.get('top_issues', []), ensure_ascii=False)}
- 급증 이슈: {json.dumps(analysis_data.get('emerging_issues', []), ensure_ascii=False)}
- 개선 권고: {json.dumps(analysis_data.get('recommendations', []), ensure_ascii=False)}
- 통계: {json.dumps(analysis_data.get('stats', {}), ensure_ascii=False)}

## 산업 컨텍스트
- 산업: {ind['name']}
- 주요 리스크: {ind['risks']}
- 핵심 부서: {ind['departments']}
- 모니터링 채널: {ind['channels']}

## 출력 형식
{{
  "meeting_title": "긴급 {ind['name']} 리스크 대응 회의",
  "urgency": "긴급",
  "estimated_duration": "60분",
  "attendees": [
    {{"department": "부서명", "role": "직책", "reason": "참석 사유"}}
  ],
  "agenda_items": [
    {{
      "order": 1,
      "title": "멀티채널 리스크 현황 보고",
      "priority": "critical",
      "duration": "15분",
      "presenter": "발표 부서",
      "discussion_points": [
        "채널별 부정 피드백 현황",
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
4. attendees에 {ind['name']} 산업에 적합한 부서명과 참석 사유를 명시
5. action_items에 구체적인 담당자와 기한 포함
6. agenda_items는 3~5개로 구성
7. {ind['departments']} 중 관련 부서를 참석자로 포함하세요"""

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


# ──────────────────────────────────────────
# Demo Scenario (OO 충전기 폭발 사건)
# ──────────────────────────────────────────

DEMO_SIGNALS = [
    {
        "platform": "Coupang",
        "channel_type": "internal",
        "data_type": "Product Review",
        "item_name": "초소형 고속 충전기 65W",
        "content": "사용 중에 퍽 소리가 나면서 타는 냄새가 나요. 아이 방에서 쓰다가 불날 뻔했습니다. 제품 결함 같은데 환불해주세요.",
        "metadata": {
            "rating": 1, "is_verified_purchase": True, "timestamp": "2026-02-20T10:30:00Z"
        },
        "risk_indicators": ["화재위험", "폭발", "안전결함"],
    },
    {
        "platform": "YouTube",
        "channel_type": "external",
        "data_type": "Video Comment",
        "video_title": "[리뷰] 가성비 끝판왕 OO 충전기 한 달 사용기",
        "channel_name": "테크마스터TV",
        "content": "이거 저도 샀는데 커뮤니티 보니까 저만 터진 게 아니더라고요. 제조사 대응도 엉망이라는데 불매해야 하는 거 아님?",
        "metadata": {
            "likes": 156, "replies_count": 24,
            "author_subscriber_count": 500, "timestamp": "2026-02-20T11:15:00Z"
        },
        "risk_indicators": ["불매운동 징후", "집단 불만", "확산성 높음"],
    },
    {
        "platform": "Naver Blog",
        "channel_type": "external",
        "data_type": "Blog Post",
        "post_title": "실제 경험담: OO 충전기 폭발 사고와 제조사의 무책임한 대응",
        "content": "충전기가 터져서 멀티탭까지 다 탔습니다. 업체에 전화했더니 사용자 과실이라며 보상을 거부하네요. 소비자원에 고발할 예정입니다. (사진 첨부)",
        "metadata": {
            "visitor_count": 1200, "is_top_exposure": True, "timestamp": "2026-02-19T18:00:00Z"
        },
        "risk_indicators": ["법적 분쟁", "증거 포함", "고노출 데이터"],
    },
    {
        "platform": "Community (뽐뿌)",
        "channel_type": "external",
        "data_type": "Post Text",
        "post_title": "형들 이번 OO 충전기 이슈 정리해준다.txt",
        "content": "회로 설계 자체가 65W를 못 버티게 설계됨. 뜯어보니까 콘덴서 싸구려 썼네. 이거 조만간 터질 일만 남았다 다들 쓰지 마라.",
        "metadata": {
            "view_count": 4500, "recommend_count": 89,
            "board_name": "자유게시판", "timestamp": "2026-02-20T13:45:00Z"
        },
        "risk_indicators": ["기술적 결함 폭로", "전문가 분석 포함", "여론 선동"],
    },
]


def _demo_signals_text() -> str:
    return json.dumps(DEMO_SIGNALS, ensure_ascii=False, indent=2)


def _demo_generate_ontology(client) -> dict:
    signals_text = _demo_signals_text()
    prompt = f"""다음은 4개 채널에서 동시에 감지된 동일 사건의 데이터입니다.

## 감지된 신호 (4개 채널)
{signals_text}

## 분석 지시
이 4개 데이터는 모두 동일한 "OO 충전기 폭발/화재 사건"으로 클러스터링됩니다.
온톨로지 엔진으로 이 사건의 인과관계 지식 그래프를 생성하세요.

핵심 포인트:
- 4개 채널(Coupang, YouTube, Naver Blog, Community)이 하나의 사건 노드로 연결됨
- 안전 사고 → 법적 분쟁 → 집단 보이콧 → 브랜드 위기 흐름을 표현
- severity 10짜리 RED 리스크 노드 포함

## 출력 형식
{{
  "nodes": [
    {{"id": "n1", "label": "노드명", "type": "category|root_cause|department|risk_type|channel", "severity": 8}}
  ],
  "links": [
    {{"source": "n1", "target": "n2", "relation": "관계명"}}
  ],
  "summary": "4개 채널 동시 감지 → 치명적 리스크 격상 요약 (2-3문장)"
}}

노드 20~28개, 채널 노드 4개 포함 필수. risk_type 노드에 severity 10 포함."""

    content = call_openai_json(client, prompt, system_prompt=RISK_SYSTEM_PROMPT)
    result = extract_json_from_text(content)
    if result and "nodes" in result:
        return result
    return {"nodes": [], "links": [], "summary": "온톨로지 생성 실패"}


def _demo_generate_compliance(client) -> dict:
    signals_text = _demo_signals_text()
    prompt = f"""다음 4개 채널 멀티채널 위기 감지 결과로 치명적 리스크 컴플라이언스 보고서를 생성하세요.

## 감지된 신호
{signals_text}

## 상황
- 4개 채널(이커머스 리뷰 1개 + 외부 채널 3개)에서 동일 사건 동시 감지
- 개별 채널 Yellow였으나 복합 발생으로 RED로 격상
- 법적 대응 언급, 바이럴 징후, 기술적 결함 폭로 복합 발생

## 출력 형식
{{
  "report_title": "OO 충전기 폭발 사건 긴급 리스크 보고서",
  "report_date": "2026-02-20",
  "overall_risk_level": "위험",
  "monitoring_summary": "쿠팡·YouTube·네이버 블로그·뽐뿌 4개 채널에서 동일한 충전기 화재/폭발 사건이 동시 감지되었습니다. 개별 채널 황색 경보가 복합 발생으로 치명적(RED) 수준으로 격상되었습니다. 법적 분쟁 가능성, 집단 불매운동 징후, 기술적 결함 공개 등 3중 위기가 중첩된 상태입니다.",
  "monitored_channels": [
    {{"channel": "쿠팡 리뷰", "feed_count": 1, "risk_count": 1, "status": "active"}},
    {{"channel": "YouTube 댓글", "feed_count": 1, "risk_count": 1, "status": "active"}},
    {{"channel": "네이버 블로그", "feed_count": 1, "risk_count": 1, "status": "active"}},
    {{"channel": "뽐뿌 커뮤니티", "feed_count": 1, "risk_count": 1, "status": "active"}}
  ],
  "risk_assessment": {{
    "legal": {{"level": "high", "description": "법적 리스크 설명"}},
    "reputation": {{"level": "high", "description": "평판 리스크 설명"}},
    "operational": {{"level": "high", "description": "운영 리스크 설명"}},
    "safety": {{"level": "high", "description": "안전 리스크 설명"}}
  }},
  "risk_events": [
    {{
      "id": 1, "severity": "critical", "category": "제품 안전 결함",
      "channel": "쿠팡 리뷰", "description": "설명", "affected_count": 1, "recommended_action": "즉각 리콜 검토"
    }},
    {{
      "id": 2, "severity": "high", "category": "집단 불매운동 징후",
      "channel": "YouTube 댓글", "description": "설명", "affected_count": 156, "recommended_action": "대응 공지 게시"
    }},
    {{
      "id": 3, "severity": "high", "category": "법적 분쟁 가능성",
      "channel": "네이버 블로그", "description": "설명", "affected_count": 1200, "recommended_action": "법무팀 즉각 검토"
    }},
    {{
      "id": 4, "severity": "high", "category": "기술적 결함 공개 폭로",
      "channel": "뽐뿌 커뮤니티", "description": "설명", "affected_count": 4500, "recommended_action": "제품 긴급 검수"
    }}
  ],
  "next_actions": ["즉각 조치 1", "즉각 조치 2", "즉각 조치 3"]
}}

각 risk_events의 description을 실제 내용 기반으로 상세히 작성하세요. next_actions 3개 이상."""

    content = call_openai_json(client, prompt, system_prompt=RISK_SYSTEM_PROMPT)
    result = extract_json_from_text(content)
    return result if result else {
        "report_title": "OO 충전기 폭발 사건 긴급 리스크 보고서",
        "overall_risk_level": "위험",
        "monitoring_summary": "4개 채널에서 치명적 리스크 감지됨",
        "monitored_channels": [],
        "risk_assessment": {},
        "risk_events": [],
        "next_actions": [],
    }


def _demo_generate_meeting(_client) -> dict:
    prompt = """다음 위기 상황에 대한 초긴급 경영진 대응 회의 안건을 생성하세요.

## 위기 개요
- 사건: OO 초소형 고속 충전기 65W 폭발/화재 사건
- 채널: 쿠팡(이커머스 리뷰), YouTube(불매운동 댓글), 네이버 블로그(법적 대응 선언), 뽐뿌(설계결함 폭로)
- 위기 등급: 치명적 (RED) — 4채널 동시 발생으로 격상
- 주요 리스크: 제품 안전 결함 + 법적 분쟁 + 집단 불매운동 + 기술적 결함 공개

## 출력 형식
{
  "meeting_title": "초긴급 충전기 화재 사건 경영진 대응 회의",
  "urgency": "초긴급",
  "estimated_duration": "90분",
  "attendees": [참석자 5-6명, 법무팀 필수 포함],
  "agenda_items": [안건 4-5개, priority: critical/high],
  "preparation": [사전 준비사항 3개 이상]
}

각 agenda_item에 discussion_points 2-3개, action_items 2-3개 포함. 매우 구체적으로 작성."""

    client_obj = get_client()
    content = call_openai_json(client_obj, prompt, system_prompt=RISK_SYSTEM_PROMPT)
    result = extract_json_from_text(content)
    return result if result else {
        "meeting_title": "초긴급 충전기 화재 사건 경영진 대응 회의",
        "urgency": "초긴급",
        "attendees": [],
        "agenda_items": [],
        "preparation": [],
    }


def analyze_demo_scenario() -> dict:
    """OO 충전기 폭발 사건 — 4채널 동시 감지 Mock 시나리오 분석 (병렬 LLM 호출)"""
    client = get_client()

    with ThreadPoolExecutor(max_workers=3) as executor:
        ont_future = executor.submit(_demo_generate_ontology, client)
        comp_future = executor.submit(_demo_generate_compliance, client)
        meet_future = executor.submit(_demo_generate_meeting, client)

        ontology = ont_future.result()
        compliance = comp_future.result()
        meeting = meet_future.result()

    return {
        "risk_level": "RED",
        "incident_title": "OO 충전기 폭발 사건",
        "incident_summary": (
            "쿠팡·YouTube·네이버 블로그·뽐뿌 4개 채널에서 동일 제품 결함 사건이 동시 감지되었습니다. "
            "화재위험·불매운동 징후·법적 분쟁·기술적 결함 폭로가 복합 발생하여 "
            "치명적 리스크(RED)로 자동 격상되었습니다."
        ),
        "clustering_reason": (
            "4개 채널에서 '폭발', '화재', '설계결함', '법적 대응', '불매' 키워드 동시 감지 "
            "→ 온톨로지 엔진 동일 사건 클러스터링 판정"
        ),
        "channel_signals": DEMO_SIGNALS,
        "ontology": ontology,
        "compliance": compliance,
        "meeting": meeting,
    }
