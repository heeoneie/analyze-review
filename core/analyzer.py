from collections import Counter

from core.utils.json_utils import extract_json_from_text
from core.utils.openai_client import call_openai_json, get_client
from core.utils.prompt_templates import build_zero_shot_prompt, format_reviews

SYSTEM_PROMPT_ANALYST = (
    "You are an expert at analyzing e-commerce customer "
    "feedback and identifying patterns."
)

SYSTEM_PROMPT_CONSULTANT = (
    "You are an expert business consultant specializing in "
    "e-commerce operations."
)


class ReviewAnalyzer:
    def __init__(self):
        self.client = get_client()

    def categorize_issues(self, reviews_text_list, sample_size=200):
        """Categorize issues from reviews using LLM"""
        # Sample reviews to avoid token limits
        sampled_reviews = (
            reviews_text_list[:sample_size]
            if len(reviews_text_list) > sample_size
            else reviews_text_list
        )

        reviews_text = format_reviews(sampled_reviews)
        prompt = build_zero_shot_prompt(reviews_text, len(sampled_reviews))

        content = call_openai_json(
            self.client,
            prompt,
            system_prompt=SYSTEM_PROMPT_ANALYST,
        )
        result = extract_json_from_text(content)
        if result is None:
            raise ValueError("Failed to parse categorization JSON response.")
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
        recent_categories = [
            item['category'] for item in recent_categorization.get('categories', [])
        ]
        comparison_categories = [
            item['category']
            for item in comparison_categorization.get('categories', [])
        ]

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

Based on this analysis, provide exactly 3 actionable recommendations that the business
should implement immediately.

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

        content = call_openai_json(
            self.client,
            prompt,
            system_prompt=SYSTEM_PROMPT_CONSULTANT,
        )
        result = extract_json_from_text(content)
        if result is None:
            raise ValueError("Failed to parse recommendations JSON response.")
        return result.get('recommendations', [])
