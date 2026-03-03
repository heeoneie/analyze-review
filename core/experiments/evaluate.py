# pylint: disable=wrong-import-position,wrong-import-order,ungrouped-imports
"""
Level 1: 정량적 평가 시스템
AI 예측 결과와 Ground Truth를 비교하여 정확도 측정
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime

import matplotlib

matplotlib.use('Agg')  # non-interactive backend — pyplot import 전에 반드시 호출

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core import config as _config  # pylint: disable=wrong-import-position
from core.utils.json_utils import (
    extract_json_from_text,  # pylint: disable=wrong-import-position
)
from core.utils.openai_client import (  # pylint: disable=wrong-import-position
    call_openai_json,
    get_client,
)
from core.utils.review_categories import (
    CATEGORIES_BULLETS,  # pylint: disable=wrong-import-position
)

logger = logging.getLogger(__name__)


class _NumpyEncoder(json.JSONEncoder):
    """numpy 타입을 Python 기본 타입으로 변환"""
    def default(self, o):
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        return super().default(o)


def _build_eval_prompt(reviews_text: str, review_count: int) -> str:
    """평가 전용 프롬프트 — 고정 영어 카테고리 사용 (ground truth와 일치)"""
    return (
        f"Classify {review_count} e-commerce reviews into exactly one category each.\n\n"
        "Categories (use the exact key name, no translation):\n"
        f"{CATEGORIES_BULLETS}\n"
        "Reviews:\n"
        f"{reviews_text}\n\n"
        "Output JSON:\n"
        '{{\n'
        '  "categories": [\n'
        '    {{"review_number": 1, "category": "delivery_delay", "brief_issue": "..."}},\n'
        '    ...\n'
        '  ]\n'
        '}}\n'
        "Rules: category MUST be one of the keys above (English snake_case). "
        "Never translate or create new category names."
    )


class Evaluator:
    def __init__(self, ground_truth_file='evaluation/evaluation_dataset.csv'):
        self.ground_truth_file = ground_truth_file
        self._client = get_client()
        if self._client is None:
            logger.warning("OpenAI 클라이언트 없음 — Gemini 폴백만 사용 가능")

    def load_ground_truth(self):
        """Ground Truth 데이터 로드"""
        df = pd.read_csv(self.ground_truth_file)

        # manual_label이 비어있는지 확인
        missing_mask = df['manual_label'].isna() | (df['manual_label'].str.strip() == '')
        if missing_mask.any():
            missing_count = missing_mask.sum()
            print(f"⚠️  경고: {missing_count}개 리뷰가 아직 라벨링되지 않았습니다.")
            print("   모든 리뷰를 라벨링한 후 다시 실행하세요.")
            return None

        return df

    def predict_categories(self, reviews_text_list):
        """AI로 카테고리 예측 (고정 영어 카테고리 사용)"""
        print("\n🤖 AI 예측 중...")

        reviews_text = "\n---\n".join(
            f"{i + 1}. {text[:500]}" for i, text in enumerate(reviews_text_list)
        )
        prompt = _build_eval_prompt(reviews_text, len(reviews_text_list))
        content = call_openai_json(
            self._client,
            prompt,
            system_prompt=(
                "You are an expert review classifier. "
                "Always return the exact English snake_case category key."
            ),
        )
        categorization = extract_json_from_text(content) or {}

        # 예측 결과를 리뷰 순서대로 정렬
        predictions = {}
        for item in categorization.get('categories', []):
            if not isinstance(item, dict):
                continue
            review_num = item.get('review_number')
            category = item.get('category')
            if not isinstance(review_num, int) or not isinstance(category, str):
                continue
            review_idx = review_num - 1  # 0-indexed
            if 0 <= review_idx < len(reviews_text_list):
                predictions[review_idx] = category

        # 순서대로 리스트 생성
        pred_list = [predictions.get(i, 'other') for i in range(len(reviews_text_list))]
        return pred_list

    def calculate_metrics(self, y_true, y_pred):
        """정확도 지표 계산"""
        # Overall metrics
        accuracy = accuracy_score(y_true, y_pred)

        # Per-class metrics
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true, y_pred, average='weighted', zero_division=0
        )

        # Per-class detailed metrics
        precision_per_class, recall_per_class, f1_per_class, support_per_class = (
            precision_recall_fscore_support(
                y_true,
                y_pred,
                average=None,
                zero_division=0,
                labels=sorted(set(y_true)),
            )
        )

        metrics = {
            'accuracy': round(accuracy, 4),
            'precision_weighted': round(precision, 4),
            'recall_weighted': round(recall, 4),
            'f1_weighted': round(f1, 4),
            'per_class_metrics': {}
        }

        for idx, label in enumerate(sorted(set(y_true))):
            metrics['per_class_metrics'][label] = {
                'precision': round(precision_per_class[idx], 4),
                'recall': round(recall_per_class[idx], 4),
                'f1': round(f1_per_class[idx], 4),
                'support': int(support_per_class[idx])
            }

        return metrics

    def create_confusion_matrix(self, y_true, y_pred, output_file='results/confusion_matrix.png'):
        """Confusion Matrix 생성"""
        os.makedirs('results', exist_ok=True)

        labels = sorted(set(y_true) | set(y_pred))
        cm = confusion_matrix(y_true, y_pred, labels=labels)

        plt.figure(figsize=(12, 10))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                    xticklabels=labels, yticklabels=labels)
        plt.title('Confusion Matrix')
        plt.ylabel('True Label')
        plt.xlabel('Predicted Label')
        plt.xticks(rotation=45, ha='right')
        plt.yticks(rotation=0)
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"\n📊 Confusion Matrix 저장: {output_file}")
        plt.close()

        return cm, labels

    def analyze_errors(self, df, y_true, y_pred):
        """에러 케이스 분석"""
        errors = []
        for idx, (true_label, pred_label) in enumerate(zip(y_true, y_pred, strict=True)):
            if true_label != pred_label:
                errors.append({
                    'review_id': df.iloc[idx]['review_id'],
                    'review_text': df.iloc[idx]['review_text'],
                    'true_label': true_label,
                    'predicted_label': pred_label,
                    'rating': df.iloc[idx]['rating']
                })

        return errors

    def save_results(self, metrics, errors, mode='baseline'):
        """결과 저장"""
        os.makedirs('results', exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 메트릭스 저장
        metrics_file = f'results/{mode}_metrics_{timestamp}.json'
        with open(metrics_file, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False, cls=_NumpyEncoder)
        print(f"\n💾 메트릭스 저장: {metrics_file}")

        # 에러 케이스 저장
        if errors:
            errors_file = f'results/{mode}_errors_{timestamp}.json'
            with open(errors_file, 'w', encoding='utf-8') as f:
                json.dump(errors, f, indent=2, ensure_ascii=False, cls=_NumpyEncoder)
            print(f"💾 에러 케이스 저장: {errors_file}")

    def print_results(self, metrics, errors):
        """결과 출력"""
        print("\n" + "="*80)
        print("  평가 결과")
        print("="*80)

        print("\n📊 Overall Metrics:")
        print(f"   Accuracy:  {metrics['accuracy']*100:.2f}%")
        print(f"   Precision: {metrics['precision_weighted']*100:.2f}%")
        print(f"   Recall:    {metrics['recall_weighted']*100:.2f}%")
        print(f"   F1 Score:  {metrics['f1_weighted']*100:.2f}%")

        print("\n📈 Per-Class Metrics:")
        print(f"{'Category':<25} {'Precision':<12} {'Recall':<12} {'F1':<12} {'Support':<8}")
        print("-" * 80)

        for category, class_metrics in metrics['per_class_metrics'].items():
            print(f"{category:<25} "
                  f"{class_metrics['precision']*100:>6.2f}%    "
                  f"{class_metrics['recall']*100:>6.2f}%    "
                  f"{class_metrics['f1']*100:>6.2f}%    "
                  f"{class_metrics['support']:>6}")

        if errors:
            print(f"\n❌ 총 {len(errors)}개 에러 케이스")
            print("\n   에러 예시 (처음 3개):")
            for i, error in enumerate(errors[:3], 1):
                print(f"\n   {i}. Review ID: {error['review_id']}")
                print(f"      Text: {error['review_text'][:100]}...")
                print(f"      True: {error['true_label']} → Predicted: {error['predicted_label']}")

    def evaluate(self, mode='baseline'):
        """전체 평가 실행"""
        print("="*80)
        print(f"  평가 시작 (Mode: {mode})")
        print("="*80)

        # Ground Truth 로드
        print("\n1. Ground Truth 로딩 중...")
        df = self.load_ground_truth()
        if df is None:
            return None, None

        print(f"   ✓ {len(df)}개 리뷰 로드 완료")

        # AI 예측
        print("\n2. AI 예측 실행 중...")
        reviews = df['review_text'].tolist()
        y_pred = self.predict_categories(reviews)
        y_true = df['manual_label'].tolist()

        print("   ✓ 예측 완료")

        # 메트릭스 계산
        print("\n3. 메트릭스 계산 중...")
        metrics = self.calculate_metrics(y_true, y_pred)

        # Confusion Matrix 생성
        print("\n4. Confusion Matrix 생성 중...")
        self.create_confusion_matrix(y_true, y_pred, f'results/{mode}_confusion_matrix.png')

        # 에러 분석
        print("\n5. 에러 케이스 분석 중...")
        errors = self.analyze_errors(df, y_true, y_pred)

        # 결과 저장
        print("\n6. 결과 저장 중...")
        self.save_results(metrics, errors, mode)

        # 결과 출력
        self.print_results(metrics, errors)

        print("\n" + "="*80)
        print("  평가 완료!")
        print("="*80)

        return metrics, errors


def main():
    parser = argparse.ArgumentParser(description='리뷰 분석 시스템 평가')
    parser.add_argument('--mode', type=str, default='baseline',
                        help='평가 모드 (baseline, improved, final)')
    args = parser.parse_args()

    evaluator = Evaluator()
    evaluator.evaluate(mode=args.mode)


if __name__ == "__main__":
    main()
