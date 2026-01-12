"""
Step 1: 평가용 데이터셋 생성
부정 리뷰 100개를 추출하여 수동 라벨링용 CSV 생성
"""

import pandas as pd
from data_loader import DataLoader
import random

def main():
    print("=" * 80)
    print("  평가 데이터셋 생성 중...")
    print("=" * 80)

    # 데이터 로드
    loader = DataLoader()
    print("\n1. 데이터 로딩 중...")
    df = loader.load_reviews()

    # 부정 리뷰 필터링
    print("\n2. 부정 리뷰 필터링 중...")
    negative_df = loader.filter_negative_reviews(df)

    # 랜덤 샘플링 (재현 가능하도록 seed 고정)
    print("\n3. 100개 샘플링 중...")
    random.seed(42)
    sampled_df = negative_df.sample(n=min(100, len(negative_df)), random_state=42)

    # 평가용 데이터프레임 생성
    eval_df = pd.DataFrame({
        'review_id': sampled_df['review_id'],
        'review_text': sampled_df['review_text'],
        'rating': sampled_df['rating'],
        'manual_label': '',  # 수동 라벨링용 빈 컬럼
        'notes': ''  # 메모용
    })

    # CSV 저장
    output_file = 'evaluation_dataset.csv'
    eval_df.to_csv(output_file, index=False, encoding='utf-8-sig')

    print(f"\n✅ 완료!")
    print(f"   파일: {output_file}")
    print(f"   샘플 수: {len(eval_df)}")
    print(f"\n다음 단계:")
    print(f"   1. {output_file} 파일을 엑셀에서 열기")
    print(f"   2. 'manual_label' 컬럼에 카테고리 입력")
    print(f"   3. labeling_guide.md 참고하여 일관성 있게 라벨링")

    # 카테고리 통계 (참고용)
    print(f"\n📊 평점 분포:")
    print(eval_df['rating'].value_counts().sort_index())

    # 샘플 미리보기
    print(f"\n🔍 샘플 미리보기 (처음 3개):")
    print("-" * 80)
    for idx, row in eval_df.head(3).iterrows():
        print(f"\nID: {row['review_id']}")
        print(f"Rating: {row['rating']}")
        print(f"Text: {row['review_text'][:200]}...")
        print("-" * 80)

if __name__ == "__main__":
    main()
