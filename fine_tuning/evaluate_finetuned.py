"""
Day 7: Fine-tuned 모델 평가
Fine-tuning한 모델의 성능 측정
"""

import argparse
import json
import os

import pandas as pd
from openai import OpenAI
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

import config
from utils.review_categories import CATEGORIES_BULLETS_FINETUNE

ALLOWED_CATEGORIES = {
    "delivery_delay",
    "wrong_item",
    "poor_quality",
    "damaged_packaging",
    "size_issue",
    "missing_parts",
    "not_as_described",
    "customer_service",
    "price_issue",
    "other",
}

class FinetunedEvaluator:
    def __init__(self, model_name):
        """
        Args:
            model_name: Fine-tuned 모델 이름 (예: ft:gpt-4o-mini:custom:review-classifier:xxx)
        """
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model_name = model_name

    def categorize_single(self, review_text):
        """단일 리뷰 분류"""
        system_prompt = (
            "You are an e-commerce feedback analyst expert at analyzing customer "
            "reviews and categorizing their primary complaints.\n\n"
            "Categories:\n"
            f"{CATEGORIES_BULLETS_FINETUNE}\n"
            "Return a JSON object only with this schema:\n"
            "{\"category\": \"<one of the categories above>\"}"
        )

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        "Categorize this review. Reply with JSON only, exactly "
                        "{\"category\": \"...\"}.\n"
                        "Example: \"Package arrived late\" -> "
                        "{\"category\": \"delivery_delay\"}\n"
                        f"Review: {review_text}"
                    ),
                }
            ],
            temperature=0.0,  # Deterministic
            response_format={"type": "json_object"},
        )

        raw_content = response.choices[0].message.content
        try:
            parsed = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON response: {raw_content}") from exc

        if not isinstance(parsed, dict) or "category" not in parsed:
            raise ValueError(f"Unexpected response format: {parsed}")

        category = parsed.get("category")
        if not isinstance(category, str) or not category.strip():
            raise ValueError(f"Invalid category value: {category}")

        category_norm = category.strip().lower()
        if category_norm not in ALLOWED_CATEGORIES:
            raise ValueError(f"Invalid category value: {category}")

        return category_norm

    def _run_predictions(self, df):
        predictions = []
        failures = []
        failure_previews = []

        for i, (_, row) in enumerate(df.iterrows(), start=1):
            print(f"   [{i}/{len(df)}] 예측 중...", end='\r')
            try:
                pred = self.categorize_single(row['review_text'])
                predictions.append(pred)
            except Exception as e:  # pylint: disable=broad-except
                # Keep evaluation running even if a single review fails.
                # Store only preview to avoid PII exposure
                text = row['review_text']
                preview = text[:30] + "..." if len(text) > 30 else text
                print(f"\n   ⚠️  에러 (Review {i}): {e}")
                failures.append(i)
                failure_previews.append(preview)
                predictions.append(None)

        return predictions, failures, failure_previews

    def _collect_successes(self, df, predictions):
        successes = []
        for pred, (_, row) in zip(predictions, df.iterrows()):
            if pred is None:
                continue
            successes.append((row['manual_label'], pred, row['review_text']))

        y_true = [true for true, _, _ in successes]
        y_pred = [pred for _, pred, _ in successes]
        return successes, y_true, y_pred

    def _compute_metrics(self, y_true, y_pred):
        if not y_true or len(y_true) == 0:
            return 0.0, 0.0, 0.0, 0.0
        accuracy = accuracy_score(y_true, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true, y_pred, average='weighted', zero_division=0
        )
        return accuracy, precision, recall, f1

    def _collect_errors(self, successes):
        errors = []
        for _, (true, pred, review_text) in enumerate(successes):
            if true != pred:
                # Store only preview to avoid PII exposure
                preview = review_text[:50] + "..." if len(review_text) > 50 else review_text
                errors.append({
                    'review_preview': preview,
                    'true': true,
                    'predicted': pred
                })
        return errors

    def _save_results(self, results, output_file):
        os.makedirs('results', exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

    def _print_metrics(self, metrics):
        """메트릭 출력"""
        print("="*80)
        print("  평가 결과")
        print("="*80 + "\n")
        print("📊 Overall Metrics:")
        print(f"   Accuracy:  {metrics['accuracy']*100:.2f}%")
        print(f"   Precision: {metrics['precision']*100:.2f}%")
        print(f"   Recall:    {metrics['recall']*100:.2f}%")
        print(f"   F1 Score:  {metrics['f1']*100:.2f}%\n")

    def _print_errors(self, errors):
        """에러 출력"""
        if errors:
            print(f"❌ 에러 케이스: {len(errors)}개\n")
            print("   예시 (처음 3개):")
            for i, error in enumerate(errors[:3], 1):
                print(f"\n   {i}. {error['review_preview']}")
                print(f"      True: {error['true']} → Predicted: {error['predicted']}")

    def evaluate(self, ground_truth_file):  # pylint: disable=too-many-locals
        """전체 평가 실행"""
        print("="*80)
        print(f"  Fine-tuned 모델 평가: {self.model_name}")
        print("="*80 + "\n")

        # Ground Truth 로드
        print("📂 Ground Truth 로딩...")
        df = pd.read_csv(ground_truth_file)

        # Normalize labels: strip whitespace, lowercase, drop empty/invalid
        df['manual_label'] = df['manual_label'].astype(str).str.strip().str.lower()
        valid_mask = df['manual_label'].ne('') & df['manual_label'].ne('nan')
        df = df[valid_mask & df['manual_label'].notna()]
        df = df[df['manual_label'].isin(ALLOWED_CATEGORIES)]

        print(f"   ✓ {len(df)}개 리뷰 로드\n")

        # 예측 실행
        print("🤖 Fine-tuned 모델로 예측 중...")
        predictions, failures, failure_previews = self._run_predictions(df)
        print("\n   ✓ 완료!\n")

        # 평가
        successes, y_true, y_pred = self._collect_successes(df, predictions)
        accuracy, precision, recall, f1 = self._compute_metrics(y_true, y_pred)
        errors = self._collect_errors(successes)

        metrics = {'accuracy': accuracy, 'precision': precision, 'recall': recall, 'f1': f1}
        self._print_metrics(metrics)
        self._print_errors(errors)

        # 결과 저장
        results = {
            'model': self.model_name,
            **metrics,
            'total_samples': len(df),
            'errors': len(errors),
            'failure_count': len(failures),
            'failures': failures,
            'failure_previews': failure_previews
        }

        output_file = 'results/finetuned_evaluation.json'
        self._save_results(results, output_file)
        print(f"\n💾 결과 저장: {output_file}")

        return results


def compare_models(base_results_file, finetuned_results_file):
    """Base 모델과 Fine-tuned 모델 비교"""
    print("\n" + "="*80)
    print("  모델 비교")
    print("="*80 + "\n")

    with open(base_results_file, 'r', encoding='utf-8') as f:
        base_results = json.load(f)

    with open(finetuned_results_file, 'r', encoding='utf-8') as f:
        ft_results = json.load(f)

    print(f"{'Metric':<15} {'Base Model':<15} {'Fine-tuned':<15} {'Improvement':<15}")
    print("-" * 80)

    metrics = ['accuracy', 'precision', 'recall', 'f1']
    for metric in metrics:
        base_val = base_results.get(metric, 0) * 100
        ft_val = ft_results.get(metric, 0) * 100
        improvement = ft_val - base_val

        print(f"{metric.capitalize():<15} {base_val:>6.2f}%        "
              f"{ft_val:>6.2f}%        "
              f"{improvement:>+6.2f}%")

    print("\n💡 결론:")
    if ft_results['accuracy'] > base_results['accuracy']:
        improvement_pct = (ft_results['accuracy'] - base_results['accuracy']) * 100
        print(f"   Fine-tuning으로 {improvement_pct:.1f}% 개선되었습니다!")
    else:
        print("   Fine-tuning 효과가 미미하거나 부정적입니다.")
        print("   → 학습 데이터 추가 또는 하이퍼파라미터 조정 필요")


def main():
    parser = argparse.ArgumentParser(description='Fine-tuned 모델 평가')
    parser.add_argument('--model', type=str, required=True,
                        help='Fine-tuned 모델 이름 (예: ft:gpt-4o-mini:custom:review-classifier:xxx)')
    parser.add_argument('--ground-truth', type=str,
                        default='evaluation/evaluation_dataset.csv',
                        help='Ground Truth CSV 파일')
    parser.add_argument('--compare', type=str,
                        help='비교할 Base 모델 결과 파일 (예: results/baseline_metrics.json)')
    args = parser.parse_args()

    # 평가 실행
    evaluator = FinetunedEvaluator(args.model)
    evaluator.evaluate(args.ground_truth)

    # 비교 (선택사항)
    if args.compare:
        if os.path.exists(args.compare):
            compare_models(args.compare, 'results/finetuned_evaluation.json')
        else:
            print(f"\n⚠️  비교 파일을 찾을 수 없습니다: {args.compare}")


if __name__ == "__main__":
    main()
