"""Prompt template helpers."""


def format_reviews(sampled_reviews):
    return "\n---\n".join(
        [f"{i + 1}. {text[:500]}" for i, text in enumerate(sampled_reviews)]
    )


def build_zero_shot_prompt(reviews_text, review_count):
    return (
        "You are analyzing customer reviews for an e-commerce platform.\n\n"
        f"Below are {review_count} negative customer reviews (rating ≤ 3/5).\n\n"
        "Your task:\n"
        "1. Read all reviews carefully\n"
        "2. Identify the main problem categories (e.g., delivery, product quality, "
        "wrong item, packaging, customer service, etc.)\n"
        "3. For each review, assign ONE primary problem category\n\n"
        "Reviews:\n"
        f"{reviews_text}\n\n"
        "Output format (JSON):\n"
        "{\n"
        '  "categories": [\n'
        "    {\n"
        '      "review_number": 1,\n'
        '      "category": "delivery_delay",\n'
        '      "brief_issue": "Package arrived 2 weeks late"\n'
        "    },\n"
        "    ...\n"
        "  ]\n"
        "}\n\n"
        "Use concise category names in English (lowercase with underscores).\n"
        "Common categories might include: delivery_delay, wrong_item, poor_quality, "
        "damaged_packaging, size_issue, missing_parts, customer_service, etc.\n"
    )
