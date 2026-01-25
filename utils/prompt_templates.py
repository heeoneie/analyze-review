"""Prompt template helpers."""

# JSON output format for single review categorization
SINGLE_REVIEW_JSON_FORMAT = (
    "Output JSON:\n"
    "{\n"
    '  "category": "category_name",\n'
    '  "confidence": 0.9,\n'
    '  "reasoning": "brief explanation"\n'
    "}\n"
)


def format_reviews(sampled_reviews):
    return "\n---\n".join(
        [f"{i + 1}. {text[:500]}" for i, text in enumerate(sampled_reviews)]
    )


IPHONE_CATEGORIES = """Categories (use EXACTLY these names):
- battery_issue: Battery problems (draining fast, not charging, poor backup, battery health)
- network_issue: Network/signal problems (weak WiFi, cellular, hotspot, eSIM issues)
- display_issue: Screen problems (screen defects, vibration, flickering, quality issues)
- software_issue: Software problems (bugs, updates, configuration, iOS issues, hanging)
- overheating: Device getting hot during use
- sound_issue: Speaker/audio problems (low volume, distortion, call audio issues)
- delivery_delay: Shipping/delivery took too long
- wrong_item: Received incorrect product (wrong color, model)
- poor_quality: General product quality issues (defective, broke easily)
- damaged_packaging: Package or product arrived damaged
- size_issue: Phone size complaints (too small screen, bezels)
- missing_parts: Missing accessories (no charger, no earphones, no adapter)
- not_as_described: Product doesn't match listing/description
- customer_service: Service/support issues (Flipkart, Apple support, refund problems)
- price_issue: Price-related complaints (too expensive, not worth money)
- positive_review: Actually positive review despite low rating
- other: Cannot be categorized or extremely vague"""


def build_zero_shot_prompt(reviews_text, review_count):
    return (
        "You are analyzing customer reviews for a smartphone (iPhone) e-commerce platform.\n\n"
        f"Below are {review_count} negative customer reviews (rating ≤ 3/5).\n\n"
        "Your task:\n"
        "1. Read all reviews carefully\n"
        "2. For each review, assign ONE primary problem category from the list below\n\n"
        f"{IPHONE_CATEGORIES}\n\n"
        "Reviews:\n"
        f"{reviews_text}\n\n"
        "Output format (JSON):\n"
        "{\n"
        '  "categories": [\n'
        "    {\n"
        '      "review_number": 1,\n'
        '      "category": "battery_issue",\n'
        '      "brief_issue": "Battery drains too fast"\n'
        "    },\n"
        "    ...\n"
        "  ]\n"
        "}\n\n"
        "Rules:\n"
        "1. Use ONLY the category names listed above (exact match required)\n"
        "2. Choose the PRIMARY issue if multiple exist\n"
        '3. "Battery backup" = battery_issue\n'
        '4. "Phone heating/hot" = overheating\n'
        '5. "Network/signal weak" = network_issue\n'
    )
