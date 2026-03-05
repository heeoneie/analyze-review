"""Amazon mock ingestion — K-Beauty/K-Food reviews with risk tagging.

Saves reviews to the Review table AND creates high-severity Node entries
so the KPI dashboard and risk timeline immediately update.

Pipeline: Review → detect_risk_candidate() → classify_with_llm() → match_precedent()
"""

import logging
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.database.models import Node, Review
from backend.services.legal_rag_service import match_precedent
from core.analyzer import classify_with_llm

logger = logging.getLogger(__name__)

# Fast keyword filter for risk candidate detection (lightweight pre-filter)
_RISK_CANDIDATE_KEYWORDS = frozenset([
    "rash", "burn", "allergy", "allergic", "lawsuit", "recall",
    "fda", "injury", "hospital", "scar", "toxic", "sue", "choking",
    "fake", "scam", "lie", "melt", "reaction",
])

# Simple keyword → risk label mapping (fallback for legacy compatibility)
_HIGH_RISK_KEYWORDS = {
    "rash": "Skin Irritation / Allergic Reaction",
    "lawsuit": "Legal Threat / Litigation Risk",
    "fda": "Regulatory Violation (FDA)",
    "burn": "Product Safety Hazard",
    "hospital": "Consumer Injury Report",
    "allergic": "Skin Irritation / Allergic Reaction",
    "toxic": "Chemical Safety Concern",
    "recall": "Regulatory Violation (FDA)",
}


def detect_risk_candidate(text: str) -> bool:
    """Fast keyword filter to identify potential risk reviews.

    Only candidate reviews are sent to the LLM for classification,
    saving API costs and reducing latency for safe reviews.

    Returns:
        True if the review contains any risk-related keywords.
    """
    if not text:
        return False
    lower = text.lower()
    return any(kw in lower for kw in _RISK_CANDIDATE_KEYWORDS)

MOCK_REVIEWS = [
    {
        "rating": 1,
        "title": "Caused severe rash on my face",
        "body": (
            "I used this K-Beauty snail mucin serum for two days and developed a severe rash "
            "across my cheeks and forehead. Had to go to urgent care. This should NOT be sold "
            "without proper FDA testing. Considering a lawsuit against the seller."
        ),
    },
    {
        "rating": 1,
        "title": "Chemical burn from this product",
        "body": (
            "This Korean skincare toner gave me a chemical burn. My dermatologist said the "
            "pH level is dangerously low. I ended up in the hospital ER. This product needs "
            "an immediate recall."
        ),
    },
    {
        "rating": 1,
        "title": "Allergic reaction — DO NOT BUY",
        "body": (
            "Severe allergic reaction after using this K-Beauty sheet mask. My eyes swelled shut "
            "and I had to use an EpiPen. The ingredients list doesn't even match what's in the "
            "product. Toxic chemicals not disclosed. Filing FDA complaint."
        ),
    },
    {
        "rating": 2,
        "title": "Kimchi arrived spoiled and smelled terrible",
        "body": (
            "The K-Food kimchi arrived with a bloated bag and smelled like it was fermenting "
            "way too long. Concerned about food safety. Other Amazon reviews mention similar "
            "issues — possible cold-chain failure."
        ),
    },
    {
        "rating": 2,
        "title": "Gochujang paste leaked everywhere",
        "body": (
            "Packaging was terrible. The gochujang container leaked inside the box. Everything "
            "was sticky and ruined. Product itself tasted off compared to what I buy at H-Mart. "
            "Disappointing quality control."
        ),
    },
    {
        "rating": 3,
        "title": "Sheet mask is okay but nothing special",
        "body": (
            "This K-Beauty collagen mask is average. Doesn't feel as hydrating as Korean brands "
            "I buy from Olive Young directly. Overpriced for what you get. Not bad, just meh."
        ),
    },
    {
        "rating": 4,
        "title": "Love this sunscreen but shipping was slow",
        "body": (
            "The Korean sunscreen SPF50 is amazing — lightweight, no white cast. Only issue "
            "is it took 3 weeks to arrive. Would buy again if shipping improves."
        ),
    },
    {
        "rating": 5,
        "title": "Best tteokbokki sauce ever!",
        "body": (
            "Authentic Korean rice cake sauce! Tastes exactly like what I had in Seoul. "
            "Perfect spice level. Already ordered 3 more bottles for friends."
        ),
    },
    {
        "rating": 3,
        "title": "Expiration date concerns",
        "body": (
            "The K-Food ramen bundle arrived with only 2 months until expiration. For the price "
            "I paid, I expected at least 6 months. Feels like they're dumping old stock on "
            "Amazon. Not cool."
        ),
    },
    {
        "rating": 1,
        "title": "Fake product — not the real Korean brand",
        "body": (
            "This is NOT genuine Sulwhasoo. The packaging is different, the texture is wrong, "
            "and it irritated my skin. This seller is selling counterfeit K-Beauty products. "
            "Amazon needs to crack down on this. Reporting to FTC."
        ),
    },
]


def _classify_severity(text: str) -> tuple[float, str | None]:
    """Return (severity_score, risk_label) using LLM classification.

    Pipeline:
    1. detect_risk_candidate() → Fast keyword filter
    2. classify_with_llm() → LLM-based classification (only for candidates)
    3. Return severity and risk category

    Stability: Always returns safe fallback on any failure.
    """
    # Fast path: skip LLM for non-candidate reviews
    if not detect_risk_candidate(text):
        return 2.0, None

    # LLM classification for risk candidates
    try:
        classification = classify_with_llm(text)
        severity = classification["severity"]
        risk_category = classification["risk_category"]

        # Map risk_category to display label
        if risk_category == "Safe":
            return severity, None

        # Use risk_category as the label (matches legal_cases.json categories)
        return severity, risk_category

    except Exception as e:  # pylint: disable=broad-except
        # Fallback to simple keyword matching if LLM fails
        logger.warning("LLM classification failed, using keyword fallback: %s", e)
        lower = text.lower()
        for keyword, label in _HIGH_RISK_KEYWORDS.items():
            if re.search(rf"\b{keyword}\b", lower):
                return 9.0, label
        return 2.0, None


def ingest_amazon_mock(product_url: str, db: Session) -> dict:  # pylint: disable=too-many-locals
    """Save 10 mock Amazon reviews + risk nodes into SQLite. Return summary."""
    reviews_saved = 0
    risks_created = 0
    now = datetime.now(timezone.utc)

    for item in MOCK_REVIEWS:
        # Check for duplicate review (idempotency)
        existing_review = (
            db.query(Review.id)
            .filter(
                Review.source == "amazon",
                Review.product_url == product_url,
                Review.title == item["title"],
                Review.body == item["body"],
            )
            .first()
        )
        if existing_review:
            continue

        full_text = f"{item['title']} {item['body']}"
        severity, risk_label = _classify_severity(full_text)

        review = Review(
            source="amazon",
            product_url=product_url,
            rating=item["rating"],
            title=item["title"],
            body=item["body"],
            severity=severity,
            risk_label=risk_label,
        )
        db.add(review)
        reviews_saved += 1

        # Only process legal RAG for severity >= 4 (skip Safe reviews)
        if severity < 4.0 or risk_label is None:
            continue

        # Create or update a Node for medium+ severity reviews
        if severity >= 4.0:
            precedent_result = match_precedent(full_text, risk_category=risk_label)
            # Dynamic Legal Exposure using confidence-weighted expected exposure
            if precedent_result:
                primary = precedent_result["primary_match"]
                expected_exposure = precedent_result["expected_exposure_usd"]
                # Scale by severity (0-10 normalized to 0-1)
                dynamic_exposure = int(expected_exposure * (severity / 10.0))
                case_id = primary["case_id"]
            else:
                dynamic_exposure = 0
                case_id = None

            normalized = (risk_label or "unknown risk").strip().lower()
            existing_node = (
                db.query(Node)
                .filter(Node.normalized_name == normalized, Node.type == "event")
                .first()
            )
            if existing_node:
                existing_node.severity_score = max(existing_node.severity_score or 0, severity)
                existing_node.last_seen_at = now
                # Update precedent info if available
                if precedent_result:
                    existing_node.case_id = case_id
                    existing_node.estimated_loss_usd = max(
                        existing_node.estimated_loss_usd or 0, dynamic_exposure
                    )
            else:
                node = Node(
                    name=risk_label or "Unknown Risk",
                    normalized_name=normalized,
                    type="event",
                    severity_score=severity,
                    case_id=case_id,
                    estimated_loss_usd=dynamic_exposure,
                    source="amazon",
                    created_at=now,
                    last_seen_at=now,
                )
                db.add(node)
            risks_created += 1

    db.commit()

    return {
        "product_url": product_url,
        "reviews_ingested": reviews_saved,
        "risks_detected": risks_created,
        "source": "amazon (mock)",
    }
