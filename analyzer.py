import json
import logging
import re
from openai import OpenAI
import config
from collections import Counter

logger = logging.getLogger(__name__)


def extract_json_from_text(text):
    """Extract JSON content from a response string with basic sanitization."""
    match = re.search(r"```(?:json)?\n(.*?)\n```", text, re.S | re.I)
    if match:
        candidate = match.group(1).strip()
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start:end + 1]
        else:
            candidate = text.strip()

    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        logger.warning("Initial JSON parse failed: %s; raw response: %s", exc, text)
        repaired = candidate.replace("{{", "{").replace("}}", "}")
        repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            logger.error("Repaired JSON still invalid. Returning empty object.")
            return {}

class ReviewAnalyzer:
    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.LLM_MODEL
        self.temperature = config.LLM_TEMPERATURE

    def categorize_issues(self, reviews_text_list, sample_size=200):
        """Categorize issues from reviews using LLM"""
        # Sample reviews to avoid token limits
        sampled_reviews = reviews_text_list[:sample_size] if len(reviews_text_list) > sample_size else reviews_text_list

        reviews_text = "\n---\n".join([f"{i+1}. {text[:500]}" for i, text in enumerate(sampled_reviews)])

        prompt = f"""You are analyzing customer reviews for an e-commerce platform.

Below are {len(sampled_reviews)} negative customer reviews (rating ≤ 3/5).

Your task:
1. Read all reviews carefully
2. Identify the main problem categories (e.g., delivery, product quality, wrong item, packaging, customer service, etc.)
3. For each review, assign ONE primary problem category

Reviews:
{reviews_text}

Output format (JSON):
{{
  "categories": [
    {{
      "review_number": 1,
      "category": "delivery_delay",
      "brief_issue": "Package arrived 2 weeks late"
    }},
    ...
  ]
}}

Use concise category names in English (lowercase with underscores).
Common categories might include: delivery_delay, wrong_item, poor_quality, damaged_packaging, size_issue, missing_parts, customer_service, etc.
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert at analyzing e-commerce customer feedback and identifying patterns."},
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature,
            response_format={"type": "json_object"}
        )

        result = extract_json_from_text(response.choices[0].message.content)
        return result

    def get_top_issues(self, categorization_result, top_n=3):
        """Extract top N issues from categorization result"""
        categories = categorization_result.get('categories', [])
        category_list = [item['category'] for item in categories]

        # Count occurrences
        category_counts = Counter(category_list)
        top_issues = category_counts.most_common(top_n)

        # Get example reviews for each top issue
        top_issues_with_examples = []
        for category, count in top_issues:
            examples = [
                item['brief_issue']
                for item in categories
                if item['category'] == category
            ][:3]  # Get up to 3 examples

            top_issues_with_examples.append({
                'category': category,
                'count': count,
                'percentage': round(count / len(categories) * 100, 1),
                'examples': examples
            })

        return top_issues_with_examples

    def detect_emerging_issues(self, recent_categorization, comparison_categorization):
        """Detect issues that are increasing in the recent period"""
        recent_categories = [item['category'] for item in recent_categorization.get('categories', [])]
        comparison_categories = [item['category'] for item in comparison_categorization.get('categories', [])]

        recent_counts = Counter(recent_categories)
        comparison_counts = Counter(comparison_categories)

        # Calculate increase rate for each category
        emerging = []
        for category in recent_counts:
            recent_count = recent_counts[category]
            comparison_count = comparison_counts.get(category, 0)

            # Calculate rate (avoiding division by zero)
            if comparison_count == 0:
                if recent_count >= 5:  # Only consider if significant volume
                    increase_rate = float('inf')
                else:
                    continue
            else:
                increase_rate = (recent_count - comparison_count) / comparison_count

            # Only consider if there's an increase
            if increase_rate > 0.2:  # At least 20% increase
                emerging.append({
                    'category': category,
                    'recent_count': recent_count,
                    'comparison_count': comparison_count,
                    'increase_rate': round(increase_rate * 100, 1)
                })

        # Sort by increase rate
        emerging.sort(key=lambda x: x['increase_rate'], reverse=True)

        return emerging[:3]  # Return top 3 emerging issues

    def generate_action_plan(self, top_issues, emerging_issues):
        """Generate actionable recommendations based on analysis"""
        top_issues_text = "\n".join([
            f"- {issue['category']}: {issue['count']} mentions ({issue['percentage']}%)"
            for issue in top_issues
        ])

        emerging_text = "\n".join([
            f"- {issue['category']}: increased by {issue['increase_rate']}% "
            f"({issue['comparison_count']} → {issue['recent_count']})"
            for issue in emerging_issues
        ]) if emerging_issues else "No significant emerging issues detected."

        prompt = f"""You are a business consultant analyzing e-commerce customer feedback.

TOP 3 ISSUES (by frequency):
{top_issues_text}

EMERGING ISSUES (increasing trend):
{emerging_text}

Based on this analysis, provide exactly 3 actionable recommendations that the business should implement immediately.

Requirements:
- Each recommendation should be ONE clear, specific action
- Focus on what will have the biggest impact on customer satisfaction
- Be practical and implementable
- Write in Korean (한국어)

Output format (JSON):
{{
  "recommendations": [
    "첫 번째 구체적인 개선 액션",
    "두 번째 구체적인 개선 액션",
    "세 번째 구체적인 개선 액션"
  ]
}}
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert business consultant specializing in e-commerce operations."},
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature,
            response_format={"type": "json_object"}
        )

        result = extract_json_from_text(response.choices[0].message.content)
        return result.get('recommendations', [])
