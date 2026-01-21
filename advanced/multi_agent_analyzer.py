"""
Level 4-1: 멀티 에이전트 시스템
Self-Consistency를 통한 정확도 향상
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from openai import OpenAI
import config
from utils.json_utils import extract_json_from_text
from collections import Counter
from openai import OpenAIError

class ClassificationAgent:
    """리뷰 분류 전문 에이전트"""

    def __init__(self, agent_id, perspective="general"):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.LLM_MODEL
        self.agent_id = agent_id
        self.perspective = perspective

    def categorize(self, review_text):
        """리뷰 분류"""
        if self.perspective == "general":
            system_prompt = "You are a general e-commerce review analyst. Focus on the overall customer experience."
        elif self.perspective == "operational":
            system_prompt = "You are an operations specialist. Focus on delivery, packaging, and fulfillment issues."
        elif self.perspective == "product":
            system_prompt = "You are a product quality specialist. Focus on product quality, description accuracy, and functionality."
        else:
            system_prompt = "You are an e-commerce review analyst."

        prompt = f"""Analyze this customer review and categorize the PRIMARY issue.

Review: "{review_text}"

Categories:
- delivery_delay: Shipping/delivery took too long
- wrong_item: Received incorrect product
- poor_quality: Product quality is bad
- damaged_packaging: Package or product was damaged
- size_issue: Size doesn't fit
- missing_parts: Parts are missing
- not_as_described: Product doesn't match description
- customer_service: Customer service issues
- price_issue: Price-related complaints
- other: Cannot be categorized

Think step by step:
1. What is mentioned in the review?
2. What is the PRIMARY complaint?
3. Which category best fits?

Output JSON:
{{
  "category": "category_name",
  "confidence": 0.9,
  "reasoning": "brief explanation"
}}
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        try:
            result = extract_json_from_text(response.choices[0].message.content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response from API: {e}") from e
        result['agent_id'] = self.agent_id
        
        return result


class CoordinatorAgent:
    """여러 에이전트의 결과를 종합하는 조정자"""

    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.LLM_MODEL

    def aggregate_votes(self, predictions):
        """다수결 투표"""
        if not predictions:
            return {                
                'final_category': 'other',
                'vote_count': 0,
                'total_votes': 0,
                'agreement_rate': 0.0
            }
        categories = [p['category'] for p in predictions]
        counter = Counter(categories)
        most_common = counter.most_common(1)[0]

        return {
            'final_category': most_common[0],
            'vote_count': most_common[1],
            'total_votes': len(predictions),
            'agreement_rate': most_common[1] / len(predictions)
        }

    def weighted_consensus(self, predictions):
        """신뢰도 기반 가중 합의"""
        if not predictions:
            return {
                'final_category': 'other',
                'weighted_score': 0.0,
                'total_weight': 0.0
            }
        weighted_votes = {}

        for pred in predictions:
            category = pred['category']
            confidence = pred.get('confidence', 1.0)

            if category not in weighted_votes:
                weighted_votes[category] = 0
            weighted_votes[category] += confidence

        # 최고 점수 카테고리 선택
        best_category = max(weighted_votes.items(), key=lambda x: x[1])

        return {
            'final_category': best_category[0],
            'weighted_score': best_category[1],
            'total_weight': sum(weighted_votes.values())
        }

    def llm_consensus(self, review_text, predictions):
        """LLM을 사용한 최종 판단"""
        predictions_text = "\n".join([
            f"Agent {p['agent_id']}: {p['category']} (confidence: {p.get('confidence', 'N/A')}, reasoning: {p.get('reasoning', 'N/A')})"
            for p in predictions
        ])

        prompt = f"""You are a senior analyst reviewing classifications from multiple junior analysts.

Review: "{review_text}"

Analyst predictions:
{predictions_text}

Your task:
1. Consider all analyst opinions
2. Determine the MOST ACCURATE category
3. Provide your final decision

Output JSON:
{{
  "final_category": "category_name",
  "reasoning": "why this is the best choice",
  "confidence": 0.95
}}
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a senior e-commerce analyst making final decisions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )

        result = extract_json_from_text(response.choices[0].message.content)
        return result


class MultiAgentAnalyzer:
    """멀티 에이전트 분석 시스템"""

    def __init__(self, num_agents=3, consensus_method='vote'):
        """
        Args:
            num_agents: 사용할 에이전트 수 (3 추천)
            consensus_method: 합의 방법 ('vote', 'weighted', 'llm')
        """
        self.agents = [
            ClassificationAgent(1, "general"),
            ClassificationAgent(2, "operational"),
            ClassificationAgent(3, "product")
        ][:num_agents]

        self.coordinator = CoordinatorAgent()
        self.consensus_method = consensus_method

    def analyze_review(self, review_text):
        """단일 리뷰 분석"""
        print(f"\n분석 중: {review_text[:100]}...")

        # 각 에이전트가 독립적으로 분류
        predictions = []
        for agent in self.agents:
            try:
                pred = agent.categorize(review_text)
                predictions.append(pred)
                print(f"  Agent {pred['agent_id']}: {pred['category']} (confidence: {pred.get('confidence', 'N/A')})")
            except (OpenAIError, json.JSONDecodeError, ValueError) as e:
                print(f"  Agent {agent.agent_id} 에러: {e}")

        if not predictions:
            return None

        # 합의 방법에 따라 최종 결정
        if self.consensus_method == 'vote':
            result = self.coordinator.aggregate_votes(predictions)
        elif self.consensus_method == 'weighted':
            result = self.coordinator.weighted_consensus(predictions)
        elif self.consensus_method == 'llm':
            result = self.coordinator.llm_consensus(review_text, predictions)
        else:
            result = self.coordinator.aggregate_votes(predictions)

        result['individual_predictions'] = predictions
        print(f"  → 최종 결정: {result.get('final_category', 'N/A')}")

        return result

    def analyze_batch(self, reviews_list):
        """여러 리뷰 배치 분석"""
        results = []
        for idx, review in enumerate(reviews_list):
            print(f"\n[{idx+1}/{len(reviews_list)}]", end=" ")
            result = self.analyze_review(review)
            if result:
                results.append({
                    'review_text': review,
                    'final_category': result.get('final_category'),
                    'details': result
                })
        return results


def main():
    """데모 실행"""
    print("="*80)
    print("  멀티 에이전트 리뷰 분석 시스템")
    print("="*80)

    # 테스트 리뷰
    test_reviews = [
        "Package arrived 3 weeks late, very disappointed",
        "Product quality is terrible, broke after 2 days",
        "Received blue shirt but ordered red one",
        "Box was damaged and item was scratched"
    ]

    # 멀티 에이전트 분석
    analyzer = MultiAgentAnalyzer(num_agents=3, consensus_method='vote')

    results = analyzer.analyze_batch(test_reviews)

    # 결과 출력
    print("\n" + "="*80)
    print("  분석 완료")
    print("="*80)

    for idx, result in enumerate(results, 1):
        print(f"\n{idx}. {result['review_text']}")
        print(f"   → {result['final_category']}")


if __name__ == "__main__":
    main()
