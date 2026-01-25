"""
Level 4-2: RAG 시스템 평가
Ground Truth 데이터로 RAG 기반 분류 정확도 측정
"""

import json
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

from advanced.rag_system import RAGReviewAnalyzer


def evaluate_rag(ground_truth_file: str, n_examples: int = 3):
    """RAG 시스템 평가"""
    print("=" * 80)
    print("  RAG 기반 리뷰 분류 평가")
    print("=" * 80)

    # Ground Truth 로드
    print(f"\n📂 Ground Truth 로딩: {ground_truth_file}")
    df = pd.read_csv(ground_truth_file)
    df = df[df['manual_label'].notna()]
    print(f"   ✓ {len(df)}개 리뷰 로드")

    # RAG 분석기 초기화 및 데이터 로드
    print("\n🔧 RAG 시스템 초기화...")
    analyzer = RAGReviewAnalyzer()
    analyzer.load_ground_truth(ground_truth_file)

    # 예측 실행 (Leave-one-out 방식)
    print(f"\n🤖 RAG 기반 분류 시작 (검색 예시: {n_examples}개)...")

    reviews = df['review_text'].tolist()
    y_true = df['manual_label'].tolist()
    y_pred = []

    for i, review in enumerate(reviews):
        print(f"   [{i+1}/{len(reviews)}] 분석 중...", end='\r')
        try:
            result = analyzer.categorize_with_rag(review, n_examples=n_examples)
            y_pred.append(result['category'])
        except Exception as e:
            print(f"\n   ⚠️ 에러 (Review {i+1}): {e}")
            y_pred.append('other')

    print("\n   ✓ 완료!")

    # 평가
    accuracy = accuracy_score(y_true, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average='weighted', zero_division=0
    )

    # 에러 분석
    errors = []
    for i, (true, pred) in enumerate(zip(y_true, y_pred)):
        if true != pred:
            errors.append({
                'review_id': int(df.iloc[i]['review_id']),
                'review_text': reviews[i][:100] + '...',
                'true_label': true,
                'predicted_label': pred
            })

    # 결과 출력
    print("\n" + "=" * 80)
    print("  평가 결과")
    print("=" * 80)
    print(f"\n📊 RAG 기반 분류 (검색 예시: {n_examples}개)")
    print(f"   Accuracy:  {accuracy * 100:.2f}%")
    print(f"   Precision: {precision * 100:.2f}%")
    print(f"   Recall:    {recall * 100:.2f}%")
    print(f"   F1 Score:  {f1 * 100:.2f}%")
    print(f"\n   에러: {len(errors)}개 / {len(y_true)}개")

    # 결과 저장
    os.makedirs('results', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    results = {
        'method': f'RAG (n_examples={n_examples})',
        'accuracy': round(accuracy, 4),
        'precision': round(precision, 4),
        'recall': round(recall, 4),
        'f1': round(f1, 4),
        'total_samples': len(y_true),
        'errors': len(errors),
        'error_details': errors[:10],  # 처음 10개만
        'timestamp': timestamp
    }

    output_file = f'results/rag_evaluation_{timestamp}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n💾 결과 저장: {output_file}")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='RAG 시스템 평가')
    parser.add_argument('--ground-truth', type=str,
                        default='evaluation/evaluation_dataset.csv',
                        help='Ground Truth CSV 파일')
    parser.add_argument('--n-examples', type=int, default=3,
                        help='검색할 유사 예시 개수')
    args = parser.parse_args()

    evaluate_rag(args.ground_truth, args.n_examples)
