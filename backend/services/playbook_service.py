"""Multi-Agent Response Playbook — LLM 기반 3-시나리오 대응 전략 생성."""

import json
import logging
from difflib import get_close_matches
from typing import Optional

from pydantic import BaseModel, field_validator

from core.utils.json_utils import extract_json_from_text
from core.utils.openai_client import call_openai_json, get_client

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  Pydantic response schema
# ──────────────────────────────────────────────
VALID_STRATEGIES = ["Conservative", "Moderate", "Aggressive"]
VALID_AGENTS = ["CS", "PR", "Legal"]


class ScenarioItem(BaseModel):
    strategy_name: str
    primary_agent: str
    action_steps: list[str]
    estimated_impact: str

    @field_validator("strategy_name")
    @classmethod
    def coerce_strategy(cls, v: str) -> str:
        if v in VALID_STRATEGIES:
            return v
        match = get_close_matches(v, VALID_STRATEGIES, n=1, cutoff=0.4)
        return match[0] if match else "Moderate"

    @field_validator("primary_agent")
    @classmethod
    def coerce_agent(cls, v: str) -> str:
        if v in VALID_AGENTS:
            return v
        match = get_close_matches(v, VALID_AGENTS, n=1, cutoff=0.4)
        return match[0] if match else "CS"

    @field_validator("action_steps", mode="before")
    @classmethod
    def ensure_non_empty_steps(cls, v):
        if not v or not isinstance(v, list) or len(v) == 0:
            return ["Triage immediately"]
        cleaned = [str(s) for s in v if s]
        return cleaned if cleaned else ["Triage immediately"]


class PlaybookResponse(BaseModel):
    scenarios: list[ScenarioItem]

    @field_validator("scenarios", mode="before")
    @classmethod
    def ensure_three_scenarios(cls, v):
        if not isinstance(v, list):
            return v
        # Pad to 3 if fewer
        while len(v) < 3:
            v.append({
                "strategy_name": VALID_STRATEGIES[len(v) % 3],
                "primary_agent": VALID_AGENTS[len(v) % 3],
                "action_steps": ["Triage immediately"],
                "estimated_impact": "To be determined",
            })
        return v[:3]


# ──────────────────────────────────────────────
#  DB fallback: pick most recent high-severity node
# ──────────────────────────────────────────────
def _pick_node_from_db(db) -> Optional[str]:
    """Query SQLite for the most recent high-severity node name."""
    if db is None:
        return None
    try:
        from backend.database.models import (  # pylint: disable=import-outside-toplevel
            Node,
        )

        row = (
            db.query(Node)
            .filter(Node.severity_score.isnot(None))
            .order_by(Node.last_seen_at.desc(), Node.severity_score.desc())
            .first()
        )
        return row.name if row else None
    except Exception:  # pylint: disable=broad-exception-caught
        logger.warning("DB 조회 실패, industry-only 폴백", exc_info=True)
        return None


# ──────────────────────────────────────────────
#  LLM prompt builder
# ──────────────────────────────────────────────
def _build_prompt(node_name: Optional[str], industry: str, lang: str) -> str:
    lang_instruction = (
        "Respond in Korean." if lang == "ko" else "Respond in English."
    )
    node_clause = (
        f'The specific risk node to address is: "{node_name}".'
        if node_name
        else "No specific risk node was selected. Generate a general industry-level playbook."
    )

    return f"""You are a senior enterprise risk management consultant.
{lang_instruction}

Industry context: {industry}
{node_clause}

Generate exactly 3 response scenarios as a JSON object with this EXACT structure:
{{
  "scenarios": [
    {{
      "strategy_name": "Conservative",
      "primary_agent": "CS",
      "action_steps": ["step 1", "step 2", "step 3"],
      "estimated_impact": "description of expected outcome"
    }},
    {{
      "strategy_name": "Moderate",
      "primary_agent": "PR",
      "action_steps": ["step 1", "step 2", "step 3"],
      "estimated_impact": "description of expected outcome"
    }},
    {{
      "strategy_name": "Aggressive",
      "primary_agent": "Legal",
      "action_steps": ["step 1", "step 2", "step 3"],
      "estimated_impact": "description of expected outcome"
    }}
  ]
}}

Rules:
- EXACTLY 3 scenarios, one for each strategy.
- strategy_name must be EXACTLY one of: "Conservative", "Moderate", "Aggressive".
- primary_agent must be EXACTLY one of: "CS", "PR", "Legal".
- Each scenario must have 3-5 concrete, actionable steps.
- estimated_impact should be 1-2 sentences describing the expected outcome.
- Conservative = minimal intervention, customer-first.
- Moderate = balanced PR + operational response.
- Aggressive = legal/executive escalation, proactive containment.
Return ONLY valid JSON, no markdown fences."""


# ──────────────────────────────────────────────
#  Core generation function
# ──────────────────────────────────────────────
def generate_playbook(
    node_name: Optional[str] = None,
    industry: str = "ecommerce",
    lang: str = "ko",
    db=None,
) -> dict:
    """Generate a 3-scenario response playbook via LLM.

    Applies DB fallback for node_name and strict Pydantic validation
    with up to 1 retry on structural failure.
    """
    # DB fallback if no node provided
    if not node_name:
        node_name = _pick_node_from_db(db)

    client = get_client()
    prompt = _build_prompt(node_name, industry, lang)
    system_prompt = (
        "You are an enterprise risk intelligence system. "
        "Always respond with valid JSON only. No markdown."
    )

    for attempt in range(2):  # max 1 retry
        try:
            raw = call_openai_json(client, prompt, system_prompt)
        except Exception:  # pylint: disable=broad-exception-caught
            logger.warning(
                "LLM 호출 실패 (attempt %d)", attempt + 1, exc_info=True,
            )
            if attempt == 0:
                continue
            return _safe_fallback(node_name, industry, lang)

        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            parsed = extract_json_from_text(raw)
            if parsed is None:
                if attempt == 0:
                    logger.warning(
                        "JSON 파싱 실패, 재시도 (attempt %d)", attempt + 1,
                    )
                    continue
                return _safe_fallback(node_name, industry, lang)

        try:
            result = PlaybookResponse.model_validate(parsed)
            if len(result.scenarios) == 3:
                return result.model_dump()
        except Exception:  # pylint: disable=broad-exception-caught
            if attempt == 0:
                logger.warning(
                    "Pydantic 검증 실패, 재시도 (attempt %d)", attempt + 1,
                )
                continue

    return _safe_fallback(node_name, industry, lang)


def _safe_fallback(
    node_name: Optional[str], industry: str, lang: str,
) -> dict:
    """Return a safe, schema-compliant fallback when LLM fails."""
    logger.error("LLM 생성 2회 실패 — safe fallback 반환")
    target = node_name or industry

    if lang == "ko":
        steps = [
            [
                f"{target} 관련 신호를 24시간 모니터링",
                "CS팀 내부 FAQ 준비",
                "고객 커뮤니케이션 템플릿 작성",
            ],
            [
                f"{target} 관련 공식 입장문 발표",
                "CS팀과 통합 메시징 조율",
                "주요 미디어 대상 내러티브 관리",
            ],
            [
                f"{target} 법적 리스크 검토 착수",
                "C레벨 경영진 에스컬레이션",
                "규제 컴플라이언스 문서 준비",
            ],
        ]
        impacts = [
            "최소 개입으로 고객 신뢰를 유지하며 "
            "선제적 커뮤니케이션 수행",
            "균형 잡힌 대응으로 내러티브를 통제하며 "
            "이해관계자 우려 해소",
            "법적·규제 리스크로부터 기업을 보호하는 "
            "최대 봉쇄 전략",
        ]
    else:
        steps = [
            [
                f"Monitor {target} signals for 24 hours",
                "Prepare internal FAQ for CS team",
                "Draft customer communication template",
            ],
            [
                f"Issue official statement regarding {target}",
                "Coordinate with CS for unified messaging",
                "Engage key media contacts for narrative control",
            ],
            [
                f"Initiate legal review of {target} exposure",
                "Escalate to C-level for executive decision",
                "Prepare regulatory compliance documentation",
            ],
        ]
        impacts = [
            "Minimal disruption; maintains customer trust "
            "through proactive communication.",
            "Balanced response; controls narrative "
            "while addressing stakeholder concerns.",
            "Maximum containment; protects company "
            "from legal and regulatory risk.",
        ]

    return PlaybookResponse(
        scenarios=[
            ScenarioItem(
                strategy_name="Conservative",
                primary_agent="CS",
                action_steps=steps[0],
                estimated_impact=impacts[0],
            ),
            ScenarioItem(
                strategy_name="Moderate",
                primary_agent="PR",
                action_steps=steps[1],
                estimated_impact=impacts[1],
            ),
            ScenarioItem(
                strategy_name="Aggressive",
                primary_agent="Legal",
                action_steps=steps[2],
                estimated_impact=impacts[2],
            ),
        ]
    ).model_dump()
