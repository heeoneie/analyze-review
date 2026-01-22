"""
Day 7: Fine-tuning 학습 데이터 준비
OpenAI Fine-tuning API 형식으로 변환
"""

import argparse
import json
import os

import pandas as pd
from utils.review_categories import CATEGORIES_BULLETS_FINETUNE

CATEGORIES_DESCRIPTION = {
    'delivery_delay': 'Shipping or delivery took too long',
    'wrong_item': 'Received incorrect product or wrong item',
    'poor_quality': 'Product quality is poor or defective',
    'damaged_packaging': 'Package or product was damaged during shipping',
    'size_issue': 'Product size does not fit or is incorrect',
    'missing_parts': 'Parts or accessories are missing from the package',
    'not_as_described': 'Product does not match description or photos',
    'customer_service': 'Issues with customer service response or support',
    'price_issue': 'Price-related complaints or concerns',
    'other': 'Cannot be categorized into above categories'
}

class TrainingDataPreparator:
    def __init__(self, ground_truth_file):
        self.ground_truth_file = ground_truth_file
        self.training_data = []
        self.validation_data = []

    def load_ground_truth(self):
        """Ground Truth ?????????????"""
        print(f"??? Ground Truth ??????: {self.ground_truth_file}")

        df = pd.read_csv(self.ground_truth_file)

        required_columns = {"manual_label", "review_text"}
        missing_columns = required_columns - set(df.columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

        initial_count = len(df)
        allowed_categories = set(CATEGORIES_DESCRIPTION.keys())

        df = df[df["manual_label"].notna()].copy()
        df["manual_label"] = df["manual_label"].astype(str).str.strip().str.lower()
        df = df[df["manual_label"] != ""]
        df = df[df["manual_label"].isin(allowed_categories)]

        df = df[df["review_text"].notna()].copy()
        df["review_text"] = df["review_text"].astype(str).str.strip()
        df = df[df["review_text"] != ""]

        if "category" in df.columns:
            df = df[df["category"].notna()].copy()
            df["category"] = df["category"].astype(str).str.strip().str.lower()
            df = df[df["category"] != ""]
            df = df[df["category"].isin(allowed_categories)]

        before_dedup = len(df)
        df = df.drop_duplicates(subset=["review_text"])
        deduped_count = before_dedup - len(df)
        removed_total = initial_count - len(df)

        print(
            f"   ??{len(df)}?????????????? ?????? ?????? "
            f"(?????? {removed_total}??? / ?????? {deduped_count}???)"
        )

        return df

    def create_training_example(self, review_text, category):
        """단일 학습 예시 생성 (OpenAI Format)"""
        system_prompt = (
            "You are an expert at analyzing e-commerce customer reviews and "
            "categorizing their primary complaints.\n\n"
            "Categories:\n"
            f"{CATEGORIES_BULLETS_FINETUNE}\n"
            "Respond with ONLY the category name, nothing else."
        )

        example = {
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": f"Categorize this review: {review_text}"
                },
                {
                    "role": "assistant",
                    "content": category
                }
            ]
        }

        return example

    def split_train_validation(self, df, validation_ratio=0.2):
        """Train/Validation 분리"""
        # 랜덤 셔플
        df = df.sample(frac=1, random_state=42).reset_index(drop=True)

        # 분리
        split_idx = int(len(df) * (1 - validation_ratio))
        train_df = df[:split_idx]
        val_df = df[split_idx:]

        print("\n📊 데이터 분리:")
        print(f"   Train: {len(train_df)}개")
        print(f"   Validation: {len(val_df)}개")

        return train_df, val_df

    def prepare_data(self, output_dir='fine_tuning'):
        """전체 데이터 준비"""
        os.makedirs(output_dir, exist_ok=True)

        print("="*80)
        print("  Fine-tuning 학습 데이터 준비")
        print("="*80 + "\n")

        # Ground Truth 로드
        df = self.load_ground_truth()

        # Train/Validation 분리
        train_df, val_df = self.split_train_validation(df)

        # Train 데이터 생성
        print("\n⚙️  Train 데이터 생성 중...")
        for _, row in train_df.iterrows():
            example = self.create_training_example(
                row['review_text'],
                row['manual_label']
            )
            self.training_data.append(example)

        # Validation 데이터 생성
        print("⚙️  Validation 데이터 생성 중...")
        for _, row in val_df.iterrows():
            example = self.create_training_example(
                row['review_text'],
                row['manual_label']
            )
            self.validation_data.append(example)

        # JSONL 파일로 저장
        train_file = os.path.join(output_dir, 'training_data.jsonl')
        val_file = os.path.join(output_dir, 'validation_data.jsonl')

        print("\n💾 저장 중...")
        with open(train_file, 'w', encoding='utf-8') as f:
            for example in self.training_data:
                f.write(json.dumps(example, ensure_ascii=False) + '\n')

        with open(val_file, 'w', encoding='utf-8') as f:
            for example in self.validation_data:
                f.write(json.dumps(example, ensure_ascii=False) + '\n')

        print(f"   ✓ Train: {train_file}")
        print(f"   ✓ Validation: {val_file}")

        # 통계 정보
        self.print_statistics(train_df, val_df)

        return train_file, val_file

    def print_statistics(self, train_df, val_df):
        """데이터 통계 출력"""
        print("\n" + "="*80)
        print("  데이터 통계")
        print("="*80)

        print("\n📊 Train 데이터 카테고리 분포:")
        train_counts = train_df['manual_label'].value_counts()
        for category, count in train_counts.items():
            percentage = (count / len(train_df)) * 100
            print(f"   {category:<25}: {count:>3}개 ({percentage:>5.1f}%)")

        print(f"\n   총 Train 샘플: {len(train_df)}개")
        print(f"   총 Validation 샘플: {len(val_df)}개")


def main():
    parser = argparse.ArgumentParser(description='Fine-tuning 학습 데이터 준비')
    parser.add_argument('--ground-truth', type=str,
                        default='evaluation/evaluation_dataset.csv',
                        help='Ground Truth CSV 파일 경로')
    parser.add_argument('--output', type=str,
                        default='fine_tuning',
                        help='출력 디렉토리')
    args = parser.parse_args()

    if not os.path.exists(args.ground_truth):
        print(f"\n❌ 파일을 찾을 수 없습니다: {args.ground_truth}")
        print("먼저 Ground Truth를 준비하세요.")
        return

    preparator = TrainingDataPreparator(args.ground_truth)
    train_file, val_file = preparator.prepare_data(args.output)

    print("\n" + "="*80)
    print("  ✅ 준비 완료!")
    print("="*80)

    print("\n다음 단계:")
    print("1. OpenAI CLI 설치:")
    print("   pip install --upgrade openai")

    print("\n2. Fine-tuning 시작:")
    print("   openai api fine_tuning.jobs.create \\")
    print(f"     -t {train_file} \\")
    print(f"     -v {val_file} \\")
    print("     -m gpt-4o-mini-2024-07-18 \\")
    print("     --suffix \"review-classifier\"")

    print("\n3. 진행 상황 확인:")
    print("   openai api fine_tuning.jobs.list")

    print("\n4. 완료 후 모델 사용:")
    print("   모델 이름: ft:gpt-4o-mini:custom:review-classifier:xxx")


if __name__ == "__main__":
    main()
