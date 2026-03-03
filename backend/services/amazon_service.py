"""Amazon mock ingestion — K-Beauty/K-Food reviews with risk tagging.

Saves reviews to the Review table AND creates high-severity Node entries
so the KPI dashboard and risk timeline immediately update.
"""

import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.database.models import Node, Review

# Simple keyword → risk label mapping
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
    """Return (severity_score, risk_label) based on keyword matching."""
    lower = text.lower()
    for keyword, label in _HIGH_RISK_KEYWORDS.items():
        if re.search(rf"\b{keyword}\b", lower):
            return 9.0, label
    return 2.0, None


def ingest_amazon_mock(product_url: str, db: Session) -> dict:
    """Save 10 mock Amazon reviews + risk nodes into SQLite. Return summary."""
    reviews_saved = 0
    risks_created = 0
    now = datetime.now(timezone.utc)

    for item in MOCK_REVIEWS:
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

        # Create a Node for high-severity reviews (reuse existing ontology Node table)
        if severity >= 8.0:
            node = Node(
                name=risk_label or "Unknown Risk",
                normalized_name=(risk_label or "unknown risk").strip().lower(),
                type="event",
                severity_score=severity,
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
