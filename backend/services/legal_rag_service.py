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

# Thresholds for matching
_EMBEDDING_THRESHOLD = 0.25
_TF_THRESHOLD = 0.35
_TOP_K = 3  # Number of top matches to return


class PrecedentMatch(TypedDict):
    case_id: str
    risk_category: str
    case_title: str
    settlement_avg_usd: int
    confidence_score: float  # 0.0 – 1.0


class PrecedentMatchResult(TypedDict):
    """Result containing top precedent matches and exposure estimate."""
    matches: list[PrecedentMatch]
    expected_exposure_usd: int  # Confidence-weighted expected exposure
    estimated_exposure_range: tuple[int, int]  # (min_avg_usd, max_avg_usd)
    primary_match: PrecedentMatch  # Best match for backward compatibility


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


def _match_via_embedding_top_k(
    text: str, cases: list[dict], top_k: int = _TOP_K
) -> list[PrecedentMatch]:
    """Cosine similarity between input text and each case's keyword phrase.

    Returns top K matches above threshold, sorted by similarity descending.
    """
    try:
        from core.utils.openai_client import (  # pylint: disable=import-outside-toplevel
            get_client,
        )

        client = get_client()
        if client is None:
            return []

        text_vec = _get_embedding(client, text)
        scored_matches: list[tuple[float, PrecedentMatch]] = []

        for case in cases:
            keyword_phrase = ", ".join(case["trigger_keywords"])
            kw_vec = _get_embedding(client, keyword_phrase)
            sim = _cosine_similarity(text_vec, kw_vec)

            # Only include matches above threshold
            if sim >= _EMBEDDING_THRESHOLD:
                settlement = case["historical_settlement"]
                match = PrecedentMatch(
                    case_id=case["case_id"],
                    risk_category=case["risk_category"],
                    case_title=case["case_title"],
                    settlement_avg_usd=settlement["avg"],
                    confidence_score=round(min(sim, 1.0), 4),
                )
                scored_matches.append((sim, match))

        # Sort by similarity descending and return top K
        scored_matches.sort(key=lambda x: x[0], reverse=True)
        return [match for _, match in scored_matches[:top_k]]

    except Exception:  # pylint: disable=broad-except
        logger.warning("Embedding RAG failed, falling back to TF scoring", exc_info=True)
        return []


# ── TF (Term Frequency) fallback ──────────────────────────────────

def _match_via_tf_top_k(
    text: str, cases: list[dict], top_k: int = _TOP_K
) -> list[PrecedentMatch]:
    """Weighted keyword-frequency scoring as deterministic fallback.

    Returns top K matches above threshold, sorted by score descending.
    """
    text_lower = text.lower()
    scored_matches: list[tuple[float, int, PrecedentMatch]] = []

    for case in cases:
        keywords = case["trigger_keywords"]
        hits = sum(1 for kw in keywords if kw in text_lower)
        if hits == 0:
            continue

        # Confidence = matched keywords / total keywords in this case
        confidence = hits / len(keywords)

        # Only include matches above threshold
        if confidence >= _TF_THRESHOLD:
            settlement = case["historical_settlement"]
            match = PrecedentMatch(
                case_id=case["case_id"],
                risk_category=case["risk_category"],
                case_title=case["case_title"],
                settlement_avg_usd=settlement["avg"],
                confidence_score=round(confidence, 4),
            )
            # Sort by hits (primary) and confidence (secondary)
            scored_matches.append((confidence, hits, match))

    # Sort by hits descending, then confidence descending
    scored_matches.sort(key=lambda x: (x[1], x[0]), reverse=True)
    return [match for _, _, match in scored_matches[:top_k]]


# ── Public API ────────────────────────────────────────────────────

def _filter_cases(cases: list[dict], risk_category: Optional[str]) -> list[dict]:
    """Filter cases by risk_category. Falls back to all cases if no match."""
    if not risk_category:
        return cases
    filtered = [c for c in cases if c["risk_category"] == risk_category]
    return filtered if filtered else cases


def match_precedent(
    text: str, risk_category: Optional[str] = None
) -> Optional[PrecedentMatchResult]:
    """Match input text against legal precedents.

    Args:
        text: Review text to match against precedents.
        risk_category: If provided, filters cases to this category first
                       (e.g. "Product Liability"). Falls back to all cases
                       if no cases match the category.

    Strategy: Category filter → Embedding cosine similarity → TF fallback.
    Returns top 3 matches with estimated exposure range.
    Returns None when no case matches above threshold.
    """
    all_cases = _load_cases()
    cases = _filter_cases(all_cases, risk_category)

    # Primary: embedding-based
    matches = _match_via_embedding_top_k(text, cases)

    # Fallback: deterministic keyword TF if embedding returns nothing
    if not matches:
        matches = _match_via_tf_top_k(text, cases)

    # No matches found
    if not matches:
        return None

    # Calculate exposure range from matched precedents
    settlement_values = [m["settlement_avg_usd"] for m in matches]
    exposure_range = (min(settlement_values), max(settlement_values))

    # Calculate confidence-weighted expected exposure
    # Formula: sum(settlement * confidence) / sum(confidence)
    weighted_sum = sum(
        m["settlement_avg_usd"] * m["confidence_score"] for m in matches
    )
    confidence_sum = sum(m["confidence_score"] for m in matches)
    expected_exposure = int(weighted_sum / confidence_sum) if confidence_sum > 0 else 0

    return PrecedentMatchResult(
        matches=matches,
        expected_exposure_usd=expected_exposure,
        estimated_exposure_range=exposure_range,
        primary_match=matches[0],  # Best match for backward compatibility
    )


# ── Legacy single-match API (backward compatibility) ───────────────

def match_single_precedent(text: str) -> Optional[PrecedentMatch]:
    """Legacy API: Returns only the best matching precedent.

    Maintained for backward compatibility with existing code.
    """
    result = match_precedent(text)
    if result is None:
        return None
    return result["primary_match"]
