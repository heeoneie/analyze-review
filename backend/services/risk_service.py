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
    {{"id": "node_5", "label": "채널명", "type": "channel", "severity": 4}},
    {{"id": "node_6", "label": "관련 인물/조직명", "type": "person", "severity": 7}},
    {{"id": "node_7", "label": "사건명", "type": "event", "severity": 9}},
    {{"id": "node_8", "label": "발생 지역/플랫폼", "type": "location", "severity": 4}},
    {{"id": "node_9", "label": "관련 법령/규정", "type": "legal_clause", "severity": 8}}
  ],
  "links": [
    {{"source": "node_1", "target": "node_2", "relation": "원인"}},
    {{"source": "node_2", "target": "node_3", "relation": "담당"}},
    {{"source": "node_1", "target": "node_4", "relation": "리스크_유발"}},
    {{"source": "node_5", "target": "node_1", "relation": "감지"}},
    {{"source": "node_6", "target": "node_7", "relation": "연루"}},
    {{"source": "node_7", "target": "node_9", "relation": "법적_적용"}},
    {{"source": "node_8", "target": "node_7", "relation": "발생지"}}
  ],
  "summary": "전체 리스크 그래프 요약 (2-3문장)"
}}

## 규칙
1. 노드 유형 9가지:
   - category(이슈 카테고리), root_cause(근본 원인), department(담당 부서)
   - risk_type(리스크 유형), channel(감지 채널)
   - person(관련 인물/조직), event(핵심 사건), location(발생 장소/플랫폼), legal_clause(관련 법령/규정)
2. 리스크 유형: 법적 분쟁, 집단 보이콧, 안전 사고, 내부 폭로, 평판 하락, 매출 감소, 고객 이탈, 규제 제재
3. 링크 관계: 원인, 담당, 리스크_유발, 대응_필요, 영향, 감지, 확산, 연루, 법적_적용, 발생지
4. 노드 18~28개 생성, severity는 1-10 스케일
5. {ind['name']} 산업의 맥락에 맞게 인물·사건·장소·법령을 구체적으로 작성하세요
6. [인물-사건-장소-법적조항] 간 인과관계를 링크로 반드시 표현하세요
7. 채널 노드를 포함하여 어디서 이슈가 감지되었는지 표현하세요"""

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
# Demo Scenarios (산업별 위기 시나리오)
# ──────────────────────────────────────────

DEMO_DATA = {
    "ecommerce": {
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
        "signals": [
            {
                "platform": "Coupang",
                "channel_type": "internal",
                "data_type": "Product Review",
                "item_name": "초소형 고속 충전기 65W",
                "content": (
                    "사용 중에 퍽 소리가 나면서 타는 냄새가 나요. "
                    "아이 방에서 쓰다가 불날 뻔했습니다. 제품 결함 같은데 환불해주세요."
                ),
                "metadata": {
                    "rating": 1, "is_verified_purchase": True,
                    "timestamp": "2026-02-20T10:30:00Z",
                },
                "risk_indicators": ["화재위험", "폭발", "안전결함"],
                "metric_label": "유사 민원 리뷰",
                "viral_risk": "보통",
                "comment_growth": [
                    {"t": "+5분", "delta": 2},
                    {"t": "+10분", "delta": 5},
                    {"t": "+20분", "delta": 9},
                ],
            },
            {
                "platform": "YouTube",
                "channel_type": "external",
                "data_type": "Video Comment",
                "video_title": "[리뷰] 가성비 끝판왕 OO 충전기 한 달 사용기",
                "channel_name": "테크마스터TV",
                "content": (
                    "이거 저도 샀는데 커뮤니티 보니까 저만 터진 게 아니더라고요. "
                    "제조사 대응도 엉망이라는데 불매해야 하는 거 아님?"
                ),
                "metadata": {
                    "likes": 156, "replies_count": 24,
                    "author_subscriber_count": 500, "timestamp": "2026-02-20T11:15:00Z",
                },
                "risk_indicators": ["불매운동 징후", "집단 불만", "확산성 높음"],
                "metric_label": "대댓글",
                "viral_risk": "높음",
                "comment_growth": [
                    {"t": "+5분", "delta": 8},
                    {"t": "+10분", "delta": 19},
                    {"t": "+20분", "delta": 41},
                ],
            },
            {
                "platform": "Naver Blog",
                "channel_type": "external",
                "data_type": "Blog Post",
                "post_title": "실제 경험담: OO 충전기 폭발 사고와 제조사의 무책임한 대응",
                "content": (
                    "충전기가 터져서 멀티탭까지 다 탔습니다. "
                    "업체에 전화했더니 사용자 과실이라며 보상을 거부하네요. "
                    "소비자원에 고발할 예정입니다. (사진 첨부)"
                ),
                "metadata": {
                    "visitor_count": 1200, "is_top_exposure": True,
                    "timestamp": "2026-02-19T18:00:00Z",
                },
                "risk_indicators": ["법적 분쟁", "증거 포함", "고노출 데이터"],
                "metric_label": "방문자",
                "viral_risk": "높음",
                "comment_growth": [
                    {"t": "+5분", "delta": 94},
                    {"t": "+10분", "delta": 267},
                    {"t": "+20분", "delta": 531},
                ],
            },
            {
                "platform": "Community (뽐뿌)",
                "channel_type": "external",
                "data_type": "Post Text",
                "post_title": "형들 이번 OO 충전기 이슈 정리해준다.txt",
                "content": (
                    "회로 설계 자체가 65W를 못 버티게 설계됨. "
                    "뜯어보니까 콘덴서 싸구려 썼네. "
                    "이거 조만간 터질 일만 남았다 다들 쓰지 마라."
                ),
                "metadata": {
                    "view_count": 4500, "recommend_count": 89,
                    "board_name": "자유게시판", "timestamp": "2026-02-20T13:45:00Z",
                },
                "risk_indicators": ["기술적 결함 폭로", "전문가 분석 포함", "여론 선동"],
                "metric_label": "추천·공감",
                "viral_risk": "높음",
                "comment_growth": [
                    {"t": "+5분", "delta": 11},
                    {"t": "+10분", "delta": 29},
                    {"t": "+20분", "delta": 57},
                ],
            },
        ],
    },

    "hospital": {
        "incident_title": "OO 무릎 수술 후 괴사 의혹 사건",
        "incident_summary": (
            "네이버 병원리뷰·YouTube·의료 커뮤니티·뉴스 4개 채널에서 동일 의료사고 의혹이 "
            "동시 확산되고 있습니다. 수술 후 합병증·의료진 부재·집단 법적 대응 예고가 "
            "복합 발생하여 치명적 리스크(RED)로 자동 격상되었습니다."
        ),
        "clustering_reason": (
            "4개 채널에서 '괴사', '의료사고', '의사 부재', '집단소송', '내부 제보' 키워드 동시 감지 "
            "→ 온톨로지 엔진 동일 사건 클러스터링 판정"
        ),
        "signals": [
            {
                "platform": "Naver 병원리뷰",
                "channel_type": "internal",
                "data_type": "Hospital Review",
                "item_name": "OO 무릎 인공관절 수술",
                "content": (
                    "수술 후 3주가 지났는데 오히려 통증이 심해지고 발이 붓습니다. "
                    "담당 교수님은 정상이라고만 하는데 다른 병원에서는 조직 일부 괴사 의심이라고 하네요."
                ),
                "metadata": {
                    "rating": 1, "is_verified_purchase": True,
                    "timestamp": "2026-02-20T09:20:00Z",
                },
                "risk_indicators": ["의료사고 의혹", "괴사 징후", "진단 불일치"],
                "metric_label": "유사 피해 리뷰",
                "viral_risk": "보통",
                "comment_growth": [
                    {"t": "+5분", "delta": 3},
                    {"t": "+10분", "delta": 7},
                    {"t": "+20분", "delta": 14},
                ],
            },
            {
                "platform": "YouTube",
                "channel_type": "external",
                "data_type": "Video Comment",
                "video_title": "OO병원 수술 후기 | 무릎 인공관절 실제 경험",
                "channel_name": "의료피해자연대",
                "content": (
                    "저도 같은 병원에서 같은 수술 받았는데 현재 법적 대응 준비 중입니다. "
                    "피해자가 저 포함 7명으로 늘었어요. 변호사 선임했고 다음 주 기자회견 예정."
                ),
                "metadata": {
                    "likes": 892, "replies_count": 143,
                    "author_subscriber_count": 12000, "timestamp": "2026-02-20T10:50:00Z",
                },
                "risk_indicators": ["집단 법적 대응", "기자회견 예고", "피해자 다수"],
                "metric_label": "공감·좋아요",
                "viral_risk": "높음",
                "comment_growth": [
                    {"t": "+5분", "delta": 34},
                    {"t": "+10분", "delta": 89},
                    {"t": "+20분", "delta": 210},
                ],
            },
            {
                "platform": "의사갤러리 (DC Inside)",
                "channel_type": "external",
                "data_type": "Community Post",
                "post_title": "OO병원 내부 의료진입니다. 더 이상 못 참겠어서 씁니다",
                "content": (
                    "해당 수술 당일 집도의가 3건 동시 진행했습니다. "
                    "실제 수술실에 있던 건 전공의였고 교수는 중간에 들어왔다 나갔습니다. "
                    "이건 명백한 대리수술입니다. 곧 내부 고발 예정."
                ),
                "metadata": {
                    "view_count": 28000, "recommend_count": 445,
                    "board_name": "의료/병원", "timestamp": "2026-02-19T22:30:00Z",
                },
                "risk_indicators": ["대리수술 폭로", "내부 제보", "형사 고발 예고"],
                "metric_label": "조회수",
                "viral_risk": "높음",
                "comment_growth": [
                    {"t": "+5분", "delta": 180},
                    {"t": "+10분", "delta": 520},
                    {"t": "+20분", "delta": 1100},
                ],
            },
            {
                "platform": "YTN 뉴스",
                "channel_type": "external",
                "data_type": "News Article",
                "post_title": "[단독] OO의료재단, 대리수술 의혹... 피해자 집단소송 예고",
                "content": (
                    "본지 취재 결과 OO의료재단에서 수술 후 합병증을 호소하는 환자가 다수 발생했으며, "
                    "의료진 내부 제보와 피해자 7인의 진술이 확보되었습니다. "
                    "보건복지부는 특별감사 착수를 검토 중입니다."
                ),
                "metadata": {
                    "visitor_count": 45000, "is_top_exposure": True,
                    "timestamp": "2026-02-20T12:00:00Z",
                },
                "risk_indicators": ["언론 보도", "정부 감사", "특종 기사"],
                "metric_label": "기사 조회수",
                "viral_risk": "높음",
                "comment_growth": [
                    {"t": "+5분", "delta": 620},
                    {"t": "+10분", "delta": 1840},
                    {"t": "+20분", "delta": 4200},
                ],
            },
        ],
    },

    "finance": {
        "incident_title": "OO 페이 개인정보 해킹 유출 사건",
        "incident_summary": (
            "앱스토어 리뷰·YouTube·커뮤니티·뉴스 4개 채널에서 동일 해킹 피해 제보가 "
            "동시 급증하고 있습니다. 무단 결제·계좌 해킹·집단 환불 요구·금융감독원 신고가 "
            "복합 발생하여 치명적 리스크(RED)로 자동 격상되었습니다."
        ),
        "clustering_reason": (
            "4개 채널에서 '해킹', '무단결제', '개인정보유출', '집단소송', '금융감독원' 키워드 동시 감지 "
            "→ 온톨로지 엔진 동일 사건 클러스터링 판정"
        ),
        "signals": [
            {
                "platform": "Google Play 리뷰",
                "channel_type": "internal",
                "data_type": "App Review",
                "item_name": "OO 간편결제 앱 v3.0",
                "content": (
                    "갑자기 모르는 가맹점에서 49,000원이 결제됐습니다. "
                    "비밀번호도 안 쳤는데 결제가 됐고 고객센터는 연결이 안 됩니다. "
                    "계좌 연동 즉시 해제하세요. 저만 당한 게 아닌 것 같습니다."
                ),
                "metadata": {
                    "rating": 1, "is_verified_purchase": True,
                    "timestamp": "2026-02-20T08:15:00Z",
                },
                "risk_indicators": ["무단 결제", "해킹 의혹", "고객센터 마비"],
                "metric_label": "유사 피해 리뷰",
                "viral_risk": "보통",
                "comment_growth": [
                    {"t": "+5분", "delta": 12},
                    {"t": "+10분", "delta": 31},
                    {"t": "+20분", "delta": 78},
                ],
            },
            {
                "platform": "YouTube",
                "channel_type": "external",
                "data_type": "Video",
                "video_title": "[긴급] OO 페이 해킹 피해 확인 방법 + 즉시 대응 가이드",
                "channel_name": "보안전문가TV",
                "content": (
                    "현재 OO 페이 앱 서버에서 개인정보가 유출된 정황이 다크웹에서 확인됐습니다. "
                    "피해자 추산 2만 명 이상. 지금 당장 앱 삭제하고 계좌 연동 해제하세요."
                ),
                "metadata": {
                    "likes": 4200, "replies_count": 890,
                    "author_subscriber_count": 85000, "timestamp": "2026-02-20T09:30:00Z",
                },
                "risk_indicators": ["다크웹 유출 확인", "대규모 피해", "긴급 대응 촉구"],
                "metric_label": "좋아요",
                "viral_risk": "높음",
                "comment_growth": [
                    {"t": "+5분", "delta": 156},
                    {"t": "+10분", "delta": 420},
                    {"t": "+20분", "delta": 980},
                ],
            },
            {
                "platform": "보배드림 커뮤니티",
                "channel_type": "external",
                "data_type": "Community Post",
                "post_title": "OO 페이 해킹 피해자 모여라 — 집단소송 준비 중",
                "content": (
                    "현재까지 피해 접수 2,847건. 변호사 선임 완료했고 "
                    "금융감독원 집단 민원 제출 예정. "
                    "OO 페이 측은 아직도 '조사 중'이라고만 하는데 이미 증거 다 있음."
                ),
                "metadata": {
                    "view_count": 62000, "recommend_count": 1240,
                    "board_name": "자유게시판", "timestamp": "2026-02-20T10:00:00Z",
                },
                "risk_indicators": ["집단소송 조직화", "금감원 제소 예고", "증거 확보"],
                "metric_label": "추천수",
                "viral_risk": "높음",
                "comment_growth": [
                    {"t": "+5분", "delta": 240},
                    {"t": "+10분", "delta": 680},
                    {"t": "+20분", "delta": 1520},
                ],
            },
            {
                "platform": "연합뉴스",
                "channel_type": "external",
                "data_type": "News Article",
                "post_title": "[단독] 핀테크 OO페이 개인정보 유출... 피해자 3만명 추산",
                "content": (
                    "금융보안원 분석 결과 OO페이 서버에서 사용자 결제정보·계좌번호·주민번호가 "
                    "외부로 유출된 것이 확인됐습니다. "
                    "금융감독원은 즉각 현장조사에 착수했으며 서비스 일시 중단을 권고했습니다."
                ),
                "metadata": {
                    "visitor_count": 120000, "is_top_exposure": True,
                    "timestamp": "2026-02-20T11:45:00Z",
                },
                "risk_indicators": ["금감원 현장조사", "서비스 중단 권고", "언론 단독 보도"],
                "metric_label": "기사 조회수",
                "viral_risk": "높음",
                "comment_growth": [
                    {"t": "+5분", "delta": 890},
                    {"t": "+10분", "delta": 2400},
                    {"t": "+20분", "delta": 5600},
                ],
            },
        ],
    },

    "gaming": {
        "incident_title": "OO 모바일 확률 조작 의혹 사건",
        "incident_summary": (
            "구글플레이 리뷰·YouTube·인벤 커뮤니티·트위터 4개 채널에서 동일한 확률 조작 의혹이 "
            "동시 폭발적으로 확산되고 있습니다. 집단 환불 운동·공정위 신고·유사 게임사 사례 비교가 "
            "복합 발생하여 치명적 리스크(RED)로 자동 격상되었습니다."
        ),
        "clustering_reason": (
            "4개 채널에서 '확률 조작', '집단환불', '공정위 신고', '내부 제보', '게임 폐업' 키워드 동시 감지 "
            "→ 온톨로지 엔진 동일 사건 클러스터링 판정"
        ),
        "signals": [
            {
                "platform": "Google Play 리뷰",
                "channel_type": "internal",
                "data_type": "Game Review",
                "item_name": "OO 크로노워 모바일",
                "content": (
                    "공지된 전설 등급 확률 0.3%인데 실제로 3,000번 뽑아서 1개 나왔습니다. "
                    "통계적으로 0.033%입니다. 이건 확률 조작입니다. "
                    "공정거래위원회에 신고 접수 완료했습니다."
                ),
                "metadata": {
                    "rating": 1, "is_verified_purchase": True,
                    "timestamp": "2026-02-20T14:20:00Z",
                },
                "risk_indicators": ["확률 조작 의혹", "공정위 신고", "통계적 증거"],
                "metric_label": "유사 피해 리뷰",
                "viral_risk": "보통",
                "comment_growth": [
                    {"t": "+5분", "delta": 18},
                    {"t": "+10분", "delta": 45},
                    {"t": "+20분", "delta": 110},
                ],
            },
            {
                "platform": "YouTube",
                "channel_type": "external",
                "data_type": "Video",
                "video_title": "[폭로] OO 확률 조작 완전 증명 | 1만번 실측 데이터 공개",
                "channel_name": "게임폭로단",
                "content": (
                    "1만 번 실측 결과 전설 확률 실제 0.028%. 공지의 1/10 수준. "
                    "전직 개발자 제보까지 받았습니다. 서버 코드에서 확률 변조 흔적 발견. "
                    "이미 조회수 80만 넘었고 언론사 3곳에서 취재 연락 왔습니다."
                ),
                "metadata": {
                    "likes": 32000, "replies_count": 5600,
                    "author_subscriber_count": 320000, "timestamp": "2026-02-20T15:00:00Z",
                },
                "risk_indicators": ["데이터 증거", "전직 개발자 제보", "언론 취재"],
                "metric_label": "좋아요",
                "viral_risk": "높음",
                "comment_growth": [
                    {"t": "+5분", "delta": 890},
                    {"t": "+10분", "delta": 2400},
                    {"t": "+20분", "delta": 5800},
                ],
            },
            {
                "platform": "인벤 커뮤니티",
                "channel_type": "external",
                "data_type": "Community Post",
                "post_title": "OO 집단환불 운동 D-1 | 카카오페이 환불 가이드 총정리",
                "content": (
                    "현재 환불 신청자 12,400명. 카카오페이 집단환불 절차 정리해드립니다. "
                    "공정위 신고 링크도 공유. 내일 오전 10시에 OO 본사 앞 시위 예정. "
                    "언론사 카메라도 온다고 합니다."
                ),
                "metadata": {
                    "view_count": 185000, "recommend_count": 8900,
                    "board_name": "게임 자유게시판", "timestamp": "2026-02-20T16:30:00Z",
                },
                "risk_indicators": ["집단환불 조직화", "오프라인 시위", "언론 현장 취재"],
                "metric_label": "추천수",
                "viral_risk": "높음",
                "comment_growth": [
                    {"t": "+5분", "delta": 340},
                    {"t": "+10분", "delta": 920},
                    {"t": "+20분", "delta": 2100},
                ],
            },
            {
                "platform": "트위터/X",
                "channel_type": "external",
                "data_type": "Trending Hashtag",
                "post_title": "#OO_확률조작 #OO_환불운동 실시간 트렌딩 1위",
                "content": (
                    "#OO_환불운동 트렌딩 1위 등극. "
                    "전 세계 트위터 게임 커뮤니티로 확산 중. "
                    "해외 게임 유저들도 'Korean gacha scam' 키워드로 공유 시작. "
                    "글로벌 스케일 리스크로 확대 중."
                ),
                "metadata": {
                    "view_count": 2400000, "recommend_count": 45000,
                    "board_name": "트렌딩", "timestamp": "2026-02-20T17:00:00Z",
                },
                "risk_indicators": ["글로벌 확산", "해외 커뮤니티 확산", "트렌딩 1위"],
                "metric_label": "트윗 노출수",
                "viral_risk": "높음",
                "comment_growth": [
                    {"t": "+5분", "delta": 4200},
                    {"t": "+10분", "delta": 11000},
                    {"t": "+20분", "delta": 28000},
                ],
            },
        ],
    },
}


def _demo_signals_text(signals: list) -> str:
    return json.dumps(signals, ensure_ascii=False, indent=2)


def _demo_generate_ontology(client, signals_text: str, incident_context: str) -> dict:
    prompt = f"""다음은 4개 채널에서 동시에 감지된 동일 사건의 데이터입니다.

## 사건 개요
{incident_context}

## 감지된 신호 (4개 채널)
{signals_text}

## 분석 지시
이 4개 데이터는 모두 동일한 사건으로 클러스터링됩니다.
온톨로지 엔진으로 이 사건의 인과관계 지식 그래프를 생성하세요.

핵심 포인트:
- 4개 채널이 하나의 사건 노드로 연결됨
- 사건 발생 → 법적/평판 리스크 → 집단 대응 → 브랜드 위기 흐름을 표현
- [인물-사건-장소-법적조항] 간 인과관계를 반드시 포함
- severity 10짜리 RED 리스크 노드 포함

## 출력 형식
{{
  "nodes": [
    {{"id": "n1", "label": "노드명", "type": "category|root_cause|department|risk_type|channel|person|event|location|legal_clause", "severity": 8}}
  ],
  "links": [
    {{"source": "n1", "target": "n2", "relation": "관계명"}}
  ],
  "summary": "4개 채널 동시 감지 → 치명적 리스크 격상 요약 (2-3문장)"
}}

노드 22~30개, 채널 노드 4개 + person/event/location/legal_clause 각 1개 이상 필수.
risk_type 노드에 severity 10 포함."""

    content = call_openai_json(client, prompt, system_prompt=RISK_SYSTEM_PROMPT)
    result = extract_json_from_text(content)
    if result and "nodes" in result:
        return result
    return {"nodes": [], "links": [], "summary": "온톨로지 생성 실패"}


def _demo_generate_compliance(client, signals_text: str, incident_context: str) -> dict:
    prompt = f"""다음 4개 채널 멀티채널 위기 감지 결과로 치명적 리스크 컴플라이언스 보고서를 생성하세요.

## 사건 개요
{incident_context}

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


def _demo_generate_meeting(_client, incident_context: str) -> dict:
    prompt = f"""다음 위기 상황에 대한 초긴급 경영진 대응 회의 안건을 생성하세요.

## 위기 개요
{incident_context}

## 출력 형식
{{
  "meeting_title": "초긴급 충전기 화재 사건 경영진 대응 회의",
  "urgency": "초긴급",
  "estimated_duration": "90분",
  "attendees": [참석자 5-6명, 법무팀 필수 포함],
  "agenda_items": [안건 4-5개, priority: critical/high],
  "preparation": [사전 준비사항 3개 이상]
}}

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


def analyze_demo_scenario(industry: str = "ecommerce") -> dict:
    """산업별 위기 시나리오 분석 — 4채널 동시 감지 Mock (병렬 LLM 호출)"""
    data = DEMO_DATA.get(industry, DEMO_DATA["ecommerce"])
    signals = data["signals"]
    signals_text = _demo_signals_text(signals)
    incident_context = (
        f"사건명: {data['incident_title']}\n"
        f"요약: {data['incident_summary']}\n"
        f"클러스터링 근거: {data['clustering_reason']}"
    )

    client = get_client()
    with ThreadPoolExecutor(max_workers=3) as executor:
        ont_f = executor.submit(
            _demo_generate_ontology, client, signals_text, incident_context
        )
        comp_f = executor.submit(
            _demo_generate_compliance, client, signals_text, incident_context
        )
        meet_f = executor.submit(
            _demo_generate_meeting, client, incident_context
        )
        ontology = ont_f.result()
        compliance = comp_f.result()
        meeting = meet_f.result()

    return {
        "risk_level": "RED",
        "incident_title": data["incident_title"],
        "incident_summary": data["incident_summary"],
        "clustering_reason": data["clustering_reason"],
        "channel_signals": signals,
        "ontology": ontology,
        "compliance": compliance,
        "meeting": meeting,
    }
