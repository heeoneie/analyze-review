"""
Day 7: Fine-tuned 모델 평가
Fine-tuning한 모델의 성능 측정
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import json
from openai import OpenAI
import config
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

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
        system_prompt = """You are an expert at analyzing e-commerce customer reviews and categorizing their primary complaints.

Categories:
- delivery_delay: Shipping or delivery issues
- wrong_item: Received incorrect product
- poor_quality: Product quality problems
- damaged_packaging: Damaged package or product
- size_issue: Size-related issues
- missing_parts: Missing parts or accessories
- not_as_described: Product doesn't match description
- customer_service: Customer service issues
- price_issue: Price-related complaints
- other: Cannot be categorized

Return a JSON object only with this schema:
{"category": "<one of the categories above>"}"""

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Categorize this review: {review_text}"}
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

        return category.strip()

    def evaluate(self, ground_truth_file):
        """전체 평가 실행"""
        print("="*80)
        print(f"  Fine-tuned 모델 평가: {self.model_name}")
        print("="*80 + "\n")

        # Ground Truth 로드
        print("📂 Ground Truth 로딩...")
        df = pd.read_csv(ground_truth_file)
        df = df[df['manual_label'].notna()]

        print(f"   ✓ {len(df)}개 리뷰 로드\n")

        # 예측 실행
        print("🤖 Fine-tuned 모델로 예측 중...")
        predictions = []

        for i, (_, row) in enumerate(df.iterrows(), start=1):
            print(f"   [{i}/{len(df)}] 예측 중...", end='\r')

            try:
                pred = self.categorize_single(row['review_text'])
                predictions.append(pred)
            except Exception as e:
                print(f"\n   ⚠️  에러 (Review {i}): {e}")
                predictions.append('other')

        print(f"\n   ✓ 완료!\n")

        # 평가
        y_true = df['manual_label'].tolist()
        y_pred = predictions

        # 메트릭스 계산
        accuracy = accuracy_score(y_true, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true, y_pred, average='weighted', zero_division=0
        )

        # 결과 출력
        print("="*80)
        print("  평가 결과")
        print("="*80 + "\n")

        print(f"📊 Overall Metrics:")
        print(f"   Accuracy:  {accuracy*100:.2f}%")
        print(f"   Precision: {precision*100:.2f}%")
        print(f"   Recall:    {recall*100:.2f}%")
        print(f"   F1 Score:  {f1*100:.2f}%\n")

        # 에러 분석
        errors = []
        for i, (true, pred) in enumerate(zip(y_true, y_pred)):
            if true != pred:
                errors.append({
                    'review': df.iloc[i]['review_text'],
                    'true': true,
                    'predicted': pred
                })

        if errors:
            print(f"❌ 에러 케이스: {len(errors)}개\n")
            print("   예시 (처음 3개):")
            for i, error in enumerate(errors[:3], 1):
                print(f"\n   {i}. {error['review'][:100]}...")
                print(f"      True: {error['true']} → Predicted: {error['predicted']}")

        # 결과 저장
        results = {
            'model': self.model_name,
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'total_samples': len(df),
            'errors': len(errors)
        }

        os.makedirs('results', exist_ok=True)
        output_file = 'results/finetuned_evaluation.json'

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n💾 결과 저장: {output_file}")

        return results


def compare_models(base_results_file, finetuned_results_file):
    """Base 모델과 Fine-tuned 모델 비교"""
    print("\n" + "="*80)
    print("  모델 비교")
    print("="*80 + "\n")

    with open(base_results_file, 'r') as f:
        base_results = json.load(f)

    with open(finetuned_results_file, 'r') as f:
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
    import argparse

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
    results = evaluator.evaluate(args.ground_truth)

    # 비교 (선택사항)
    if args.compare:
        if os.path.exists(args.compare):
            compare_models(args.compare, 'results/finetuned_evaluation.json')
        else:
            print(f"\n⚠️  비교 파일을 찾을 수 없습니다: {args.compare}")


if __name__ == "__main__":
    main()
