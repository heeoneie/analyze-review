"""Embedding-based Micro-RAG for US case law precedent matching.

Primary: OpenAI text-embedding-3-small cosine similarity.
Fallback: Weighted TF (Term Frequency) keyword scoring when embeddings unavailable.
"""

import json
import logging
import math
from pathlib import Path
from typing import Optional, TypedDict

logger = logging.getLogger(__name__)

_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "legal_cases.json"


class PrecedentMatch(TypedDict):
    case_id: str
    risk_category: str
    case_title: str
    settlement_avg_usd: int
    confidence_score: float  # 0.0 – 1.0


def _load_cases() -> list[dict]:
    with open(_DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


# ── Embedding helpers ──────────────────────────────────────────────

_EMBED_MODEL = "text-embedding-3-small"


def _get_embedding(client, text: str) -> list[float]:
    """Fetch a single embedding vector from OpenAI."""
    resp = client.embeddings.create(model=_EMBED_MODEL, input=text)
    return resp.data[0].embedding


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _match_via_embedding(text: str, cases: list[dict]) -> Optional[PrecedentMatch]:
    """Cosine similarity between input text and each case's keyword phrase."""
    try:
        from core.utils.openai_client import (  # pylint: disable=import-outside-toplevel
            get_client,
        )

        client = get_client()
        if client is None:
            return None

        text_vec = _get_embedding(client, text)

        best: Optional[PrecedentMatch] = None
        best_sim = 0.0

        for case in cases:
            keyword_phrase = ", ".join(case["trigger_keywords"])
            kw_vec = _get_embedding(client, keyword_phrase)
            sim = _cosine_similarity(text_vec, kw_vec)

            if sim > best_sim:
                best_sim = sim
                settlement = case["historical_settlement"]
                best = PrecedentMatch(
                    case_id=case["case_id"],
                    risk_category=case["risk_category"],
                    case_title=case["case_title"],
                    settlement_avg_usd=settlement["avg"],
                    confidence_score=round(min(best_sim, 1.0), 4),
                )

        # Update final confidence after loop
        if best is not None:
            best["confidence_score"] = round(min(best_sim, 1.0), 4)

        # Threshold: require minimum 0.3 similarity to be meaningful
        if best is not None and best["confidence_score"] < 0.3:
            return None

        return best
    except Exception:  # pylint: disable=broad-except
        logger.warning("Embedding RAG failed, falling back to TF scoring", exc_info=True)
        return None


# ── TF (Term Frequency) fallback ──────────────────────────────────

def _match_via_tf(text: str, cases: list[dict]) -> Optional[PrecedentMatch]:
    """Weighted keyword-frequency scoring as deterministic fallback."""
    text_lower = text.lower()

    best: Optional[PrecedentMatch] = None
    best_score = 0

    for case in cases:
        keywords = case["trigger_keywords"]
        hits = sum(1 for kw in keywords if kw in text_lower)
        if hits == 0:
            continue

        # Confidence = matched keywords / total keywords in this case
        confidence = hits / len(keywords)
        score = hits  # absolute hit count for ranking

        if score > best_score:
            best_score = score
            settlement = case["historical_settlement"]
            best = PrecedentMatch(
                case_id=case["case_id"],
                risk_category=case["risk_category"],
                case_title=case["case_title"],
                settlement_avg_usd=settlement["avg"],
                confidence_score=round(confidence, 4),
            )

    # Threshold: require minimum 0.2 confidence to return a match
    if best is not None and best["confidence_score"] < 0.2:
        return None

    return best


# ── Public API ────────────────────────────────────────────────────

def match_precedent(text: str) -> Optional[PrecedentMatch]:
    """Match input text against legal precedents.

    Strategy: Embedding cosine similarity (primary) → TF scoring (fallback).
    Returns None when no case matches above threshold.
    """
    cases = _load_cases()

    # Primary: embedding-based
    result = _match_via_embedding(text, cases)
    if result is not None:
        return result

    # Fallback: deterministic keyword TF
    return _match_via_tf(text, cases)
