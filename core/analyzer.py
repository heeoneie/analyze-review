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

    def generate_action_plan(  # pylint: disable=too-many-locals
        self, top_issues, emerging_issues, categorization_result=None
    ):
        """Generate actionable recommendations based on analysis"""
        top_issues_text = ""
        for issue in top_issues:
            examples_text = "\n".join(
                f"    - \"{ex}\"" for ex in issue.get('examples', [])
            )
            top_issues_text += (
                f"\n### {issue['category']} ({issue['count']}건, {issue['percentage']}%)\n"
                f"  고객 원문 예시:\n{examples_text}\n"
            )

        # 카테고리별 실제 리뷰 원문 수집
        review_context = ""
        if categorization_result:
            categories = categorization_result.get('categories', [])
            top_category_names = [issue['category'] for issue in top_issues]
            for cat_name in top_category_names:
                cat_reviews = [
                    item['brief_issue']
                    for item in categories
                    if item['category'] == cat_name
                ][:5]
                if cat_reviews:
                    review_context += f"\n[{cat_name}] 고객 불만 상세:\n"
                    review_context += "\n".join(f"  - {r}" for r in cat_reviews)
                    review_context += "\n"

        emerging_text = "\n".join([
            f"- {issue['category']}: {issue['increase_rate']}% 증가 "
            f"({issue['comparison_count']}건 → {issue['recent_count']}건)"
            for issue in emerging_issues
        ]) if emerging_issues else "급증하는 이슈 없음"

        prompt = f"""아래는 이커머스 상품의 부정 리뷰 분석 결과입니다.
고객이 실제로 남긴 불만 내용을 바탕으로 구체적인 개선안을 제시해주세요.

## 상위 문제 카테고리
{top_issues_text}

## 고객 불만 상세 원문
{review_context}

## 최근 급증 이슈
{emerging_text}

위 고객 불만을 분석하여 정확히 3개의 개선안을 JSON으로 작성하세요.

요구사항:
- 각 개선안은 고객이 실제로 언급한 문제에 직접 대응해야 합니다
- "배송 개선", "품질 강화"처럼 추상적 표현 금지
- 구체적 수치, 방법, 담당 부서까지 포함
- 한국어로 작성

출력 형식:
{{
  "recommendations": [
    {{
      "title": "개선안 제목 (한 줄)",
      "problem": "어떤 고객 불만에 대한 대응인지 (실제 리뷰 근거 포함)",
      "action": "구체적 실행 방법 (누가, 무엇을, 어떻게)",
      "expected_impact": "기대 효과"
    }}
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
