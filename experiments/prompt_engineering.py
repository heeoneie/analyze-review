"""
Level 2: 프롬프트 엔지니어링 실험
Zero-shot, Few-shot, CoT, Temperature 등 다양한 전략 비교
"""

from datetime import datetime
import json
import os

from openai import OpenAIError

from evaluation.evaluate import Evaluator
from utils.json_utils import extract_json_from_text
from utils.openai_client import call_openai_json, get_client
from utils.prompt_templates import build_zero_shot_prompt, format_reviews

SYSTEM_PROMPT_ANALYST = (
    "You are an expert at analyzing e-commerce customer "
    "feedback and identifying patterns."
)

SYSTEM_PROMPT_COT = (
    "You are an expert at analyzing e-commerce customer "
    "feedback. Think step by step."
)


class PromptExperiments:
    def __init__(self):
        self.client = get_client()
        self.evaluator = Evaluator()

    def _safe_call(self, prompt, system_prompt, temperature=0.3):
        """안전하게 OpenAI API 호출"""
        try:
            content = call_openai_json(
                self.client,
                prompt,
                system_prompt=system_prompt,
                temperature=temperature,
            )
            return extract_json_from_text(content)
        except (OpenAIError, json.JSONDecodeError) as e:
            print(f"API call failed: {e}")
            return {"categories": []}

    def categorize_zero_shot(self, reviews_text_list, temperature=0.3):
        """실험 1: Zero-shot (현재 방식)"""
        print("\n🔬 실험 1: Zero-shot")

        sampled_reviews = reviews_text_list[:min(100, len(reviews_text_list))]
        reviews_text = format_reviews(sampled_reviews)
        prompt = build_zero_shot_prompt(reviews_text, len(sampled_reviews))

        return self._safe_call(prompt, SYSTEM_PROMPT_ANALYST, temperature)

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
        reviews_text = "\n---\n".join(
            [f"{i+1}. {text[:500]}" for i, text in enumerate(sampled_reviews)]
        )

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
Categories: delivery_delay, wrong_item, poor_quality, damaged_packaging, size_issue,
missing_parts, not_as_described, customer_service, price_issue, other
"""

        return self._safe_call(prompt, SYSTEM_PROMPT_ANALYST, temperature)

    def categorize_cot(self, reviews_text_list, temperature=0.3):
        """실험 3: Chain-of-Thought"""
        print("\n🔬 실험 3: Chain-of-Thought")

        sampled_reviews = reviews_text_list[:min(100, len(reviews_text_list))]
        reviews_text = "\n---\n".join(
            [f"{i+1}. {text[:500]}" for i, text in enumerate(sampled_reviews)]
        )

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

Categories: delivery_delay, wrong_item, poor_quality, damaged_packaging, size_issue,
missing_parts, not_as_described, customer_service, price_issue, other
"""

        return self._safe_call(prompt, SYSTEM_PROMPT_COT, temperature)

    def extract_predictions(self, categorization_result, num_reviews):
        """카테고리화 결과에서 예측 리스트 추출"""
        predictions = {}
        for item in categorization_result.get('categories', []):
            review_num = item['review_number'] - 1
            predictions[review_num] = item['category']

        # 순서대로 리스트 생성
        pred_list = [predictions.get(i, 'other') for i in range(num_reviews)]
        return pred_list

    def _compute_accuracy(self, y_true, y_pred):
        correct = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t == p)
        return correct / len(y_true)

    def _run_categorization(self, reviews, y_true, method, **kwargs):
        result = method(reviews, **kwargs)
        y_pred = self.extract_predictions(result, len(reviews))
        return self._compute_accuracy(y_true, y_pred)

    def _add_result(self, results, key, accuracy, description):
        results[key] = {
            'accuracy': round(accuracy, 4),
            'description': description
        }

    def _save_results(self, results):
        os.makedirs('results', exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'results/prompt_experiments_{timestamp}.json'

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        return output_file

    def _print_summary(self, results, output_file):
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

        best_strategy = max(results.items(), key=lambda x: x[1]['accuracy'])
        print(f"\n🏆 최적 전략: {best_strategy[0]}")
        print(f"   Accuracy: {best_strategy[1]['accuracy']*100:.2f}%")
        print(
            "   Improvement: "
            f"+{(best_strategy[1]['accuracy'] - baseline_acc)*100:.1f}%"
        )

    def run_all_experiments(self):
        """모든 실험 실행"""
        print("="*80)
        print("  프롬프트 엔지니어링 실험")
        print("="*80)

        # Ground Truth 로드
        print("\n📂 Ground Truth 로딩...")
        df = self.evaluator.load_ground_truth()
        if df is None:
            return {}

        reviews = df['review_text'].tolist()
        y_true = df['manual_label'].tolist()

        results = {}

        # 실험 1: Zero-shot
        print("\n" + "-"*80)
        accuracy_zero = self._run_categorization(
            reviews,
            y_true,
            self.categorize_zero_shot,
        )
        self._add_result(results, 'zero_shot', accuracy_zero, 'Baseline - No examples')
        print(f"   ✓ Accuracy: {accuracy_zero*100:.2f}%")

        # 실험 2: Few-shot (3-shot)
        print("\n" + "-"*80)
        accuracy_few = self._run_categorization(
            reviews,
            y_true,
            self.categorize_few_shot,
            num_examples=3,
        )
        self._add_result(
            results,
            'few_shot_3',
            accuracy_few,
            'Few-shot with 3 examples per category',
        )
        print(f"   ✓ Accuracy: {accuracy_few*100:.2f}%")

        # 실험 3: Chain-of-Thought
        print("\n" + "-"*80)
        accuracy_cot = self._run_categorization(
            reviews,
            y_true,
            self.categorize_cot,
        )
        self._add_result(results, 'cot', accuracy_cot, 'Chain-of-Thought reasoning')
        print(f"   ✓ Accuracy: {accuracy_cot*100:.2f}%")

        # 실험 4: Temperature 실험
        print("\n" + "-"*80)
        print("\n🔬 실험 4: Temperature Optimization")
        temps = [0.0, 0.5, 0.7]
        for temp in temps:
            accuracy_temp = self._run_categorization(
                reviews,
                y_true,
                self.categorize_few_shot,
                temperature=temp,
            )
            self._add_result(
                results,
                f'temperature_{temp}',
                accuracy_temp,
                f'Few-shot with temperature={temp}',
            )
            print(f"   Temperature {temp}: {accuracy_temp*100:.2f}%")

        output_file = self._save_results(results)
        self._print_summary(results, output_file)

        return results


def main():
    experiments = PromptExperiments()
    experiments.run_all_experiments()


if __name__ == "__main__":
    main()
