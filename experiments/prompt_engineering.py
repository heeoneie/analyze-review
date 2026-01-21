"""
Level 2: 프롬프트 엔지니어링 실험
Zero-shot, Few-shot, CoT, Temperature 등 다양한 전략 비교
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from openai import OpenAI, OpenAIError
import config
from utils.json_utils import extract_json_from_text
from datetime import datetime
from evaluation.evaluate import Evaluator

class PromptExperiments:
    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.LLM_MODEL
        self.evaluator = Evaluator()

    def categorize_zero_shot(self, reviews_text_list, temperature=0.3):
        """실험 1: Zero-shot (현재 방식)"""
        print("\n🔬 실험 1: Zero-shot")

        sampled_reviews = reviews_text_list[:min(100, len(reviews_text_list))]
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

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing e-commerce customer feedback and identifying patterns."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                response_format={"type": "json_object"}
            )
            result = extract_json_from_text(response.choices[0].message.content)
            return result
        except (OpenAIError, json.JSONDecodeError) as e:
            print(f"API call failed: {e}")
            return {"categories": []}

    def categorize_few_shot(self, reviews_text_list, num_examples=3, temperature=0.3):
        """실험 2: Few-shot Learning"""
        print(f"\n🔬 실험 2: Few-shot ({num_examples}-shot)")

        # Few-shot 예시
        examples = """
Examples:
1. "Package took 3 weeks to arrive" → delivery_delay
2. "Received wrong color, ordered blue but got red" → wrong_item
3. "Product broke after 2 days of use" → poor_quality
4. "Box was damaged and item was scratched" → damaged_packaging
5. "Too small, doesn't fit" → size_issue
"""

        sampled_reviews = reviews_text_list[:min(100, len(reviews_text_list))]
        reviews_text = "\n---\n".join([f"{i+1}. {text[:500]}" for i, text in enumerate(sampled_reviews)])

        prompt = f"""You are analyzing customer reviews for an e-commerce platform.

{examples}

Below are {len(sampled_reviews)} negative customer reviews (rating ≤ 3/5).

Your task:
1. Read all reviews carefully
2. Identify the main problem category (similar to examples above)
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
Categories: delivery_delay, wrong_item, poor_quality, damaged_packaging, size_issue, missing_parts, not_as_described, customer_service, price_issue, other
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing e-commerce customer feedback."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                response_format={"type": "json_object"}
            )
            result = extract_json_from_text(response.choices[0].message.content)
            return result
        except (OpenAIError, json.JSONDecodeError) as e:
            print(f"API call failed: {e}")
            return {"categories": []}

    def categorize_cot(self, reviews_text_list, temperature=0.3):
        """실험 3: Chain-of-Thought"""
        print("\n🔬 실험 3: Chain-of-Thought")

        sampled_reviews = reviews_text_list[:min(100, len(reviews_text_list))]
        reviews_text = "\n---\n".join([f"{i+1}. {text[:500]}" for i, text in enumerate(sampled_reviews)])

        prompt = f"""You are analyzing customer reviews for an e-commerce platform.

Below are {len(sampled_reviews)} negative customer reviews (rating ≤ 3/5).

Your task - Think step by step:
1. Read the review carefully
2. List all problems mentioned in the review
3. Identify the PRIMARY/MAIN problem (the most important one)
4. Select the category that best fits the primary problem
5. Provide a brief description

Think through each review systematically before categorizing.

Reviews:
{reviews_text}

Output format (JSON):
{{
  "categories": [
    {{
      "review_number": 1,
      "category": "delivery_delay",
      "brief_issue": "Package arrived 2 weeks late",
      "reasoning": "Review mentions both delivery and quality, but focuses more on delivery time"
    }},
    ...
  ]
}}

Categories: delivery_delay, wrong_item, poor_quality, damaged_packaging, size_issue, missing_parts, not_as_described, customer_service, price_issue, other
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing e-commerce customer feedback. Think step by step."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                response_format={"type": "json_object"}
            )
            result = extract_json_from_text(response.choices[0].message.content)
            return result
        except (OpenAIError, json.JSONDecodeError) as e:
            print(f"API call failed: {e}")
            return {"categories": []}

    def extract_predictions(self, categorization_result, num_reviews):
        """카테고리화 결과에서 예측 리스트 추출"""
        predictions = {}
        for item in categorization_result.get('categories', []):
            review_num = item['review_number'] - 1
            predictions[review_num] = item['category']

        # 순서대로 리스트 생성
        pred_list = [predictions.get(i, 'other') for i in range(num_reviews)]
        return pred_list

    def run_all_experiments(self):
        """모든 실험 실행"""
        print("="*80)
        print("  프롬프트 엔지니어링 실험")
        print("="*80)

        # Ground Truth 로드
        print("\n📂 Ground Truth 로딩...")
        df = self.evaluator.load_ground_truth()
        if df is None:
            return

        reviews = df['review_text'].tolist()
        y_true = df['manual_label'].tolist()

        results = {}

        # 실험 1: Zero-shot
        print("\n" + "-"*80)
        result_zero = self.categorize_zero_shot(reviews)
        y_pred_zero = self.extract_predictions(result_zero, len(reviews))
        accuracy_zero = sum([1 for t, p in zip(y_true, y_pred_zero, strict=True) if t == p]) / len(y_true)
        results['zero_shot'] = {
            'accuracy': round(accuracy_zero, 4),
            'description': 'Baseline - No examples'
        }
        print(f"   ✓ Accuracy: {accuracy_zero*100:.2f}%")

        # 실험 2: Few-shot (3-shot)
        print("\n" + "-"*80)
        result_few = self.categorize_few_shot(reviews, num_examples=3)
        y_pred_few = self.extract_predictions(result_few, len(reviews))
        accuracy_few = sum([1 for t, p in zip(y_true, y_pred_few, strict=True) if t == p]) / len(y_true)
        results['few_shot_3'] = {
            'accuracy': round(accuracy_few, 4),
            'description': 'Few-shot with 3 examples per category'
        }
        print(f"   ✓ Accuracy: {accuracy_few*100:.2f}%")

        # 실험 3: Chain-of-Thought
        print("\n" + "-"*80)
        result_cot = self.categorize_cot(reviews)
        y_pred_cot = self.extract_predictions(result_cot, len(reviews))
        accuracy_cot = sum([1 for t, p in zip(y_true, y_pred_cot, strict=True) if t == p]) / len(y_true)
        results['cot'] = {
            'accuracy': round(accuracy_cot, 4),
            'description': 'Chain-of-Thought reasoning'
        }
        print(f"   ✓ Accuracy: {accuracy_cot*100:.2f}%")

        # 실험 4: Temperature 실험
        print("\n" + "-"*80)
        print("\n🔬 실험 4: Temperature Optimization")
        temps = [0.0, 0.5, 0.7]
        for temp in temps:
            result_temp = self.categorize_few_shot(reviews, temperature=temp)
            y_pred_temp = self.extract_predictions(result_temp, len(reviews))
            accuracy_temp = sum([1 for t, p in zip(y_true, y_pred_temp, strict=True) if t == p]) / len(y_true)
            results[f'temperature_{temp}'] = {
                'accuracy': round(accuracy_temp, 4),
                'description': f'Few-shot with temperature={temp}'
            }
            print(f"   Temperature {temp}: {accuracy_temp*100:.2f}%")

        # 결과 저장
        os.makedirs('results', exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'results/prompt_experiments_{timestamp}.json'

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        # 결과 요약
        print("\n" + "="*80)
        print("  실험 결과 요약")
        print("="*80)
        print(f"\n{'Strategy':<30} {'Accuracy':<12} {'Improvement':<12}")
        print("-" * 80)

        baseline_acc = results['zero_shot']['accuracy']
        for strategy, data in results.items():
            improvement = (data['accuracy'] - baseline_acc) * 100
            improvement_str = f"+{improvement:.1f}%" if improvement > 0 else f"{improvement:.1f}%"
            print(f"{strategy:<30} {data['accuracy']*100:>6.2f}%     {improvement_str:>8}")

        print(f"\n📊 결과 저장: {output_file}")

        # 최적 전략 추천
        best_strategy = max(results.items(), key=lambda x: x[1]['accuracy'])
        print(f"\n🏆 최적 전략: {best_strategy[0]}")
        print(f"   Accuracy: {best_strategy[1]['accuracy']*100:.2f}%")
        print(f"   Improvement: +{(best_strategy[1]['accuracy'] - baseline_acc)*100:.1f}%")

        return results


def main():
    experiments = PromptExperiments()
    experiments.run_all_experiments()


if __name__ == "__main__":
    main()
