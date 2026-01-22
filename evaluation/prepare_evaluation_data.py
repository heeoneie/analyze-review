"""
Step 1: Prepare evaluation dataset.
Creates a CSV for manual labeling by sampling negative reviews.
"""

import argparse
import os
import random
import pandas as pd

from data_loader import DataLoader


def main():
    """
    Prepare a CSV evaluation dataset of sampled negative reviews for manual labeling.
    
    Loads reviews from DataLoader (or a custom CSV provided via --csv), filters to negative reviews,
    samples up to 100 rows deterministically (seed 42), and writes an output CSV (configurable via
    --output, default "evaluation/evaluation_dataset.csv"). The output contains columns:
    `review_id`, `review_text`, `rating`, `manual_label` (empty), and `notes` (empty). The function
    also creates the output directory if needed and prints progress messages, a rating distribution,
    and a small preview of the first three samples.
    """
    print("=" * 80)
    print("  Preparing evaluation dataset")
    print("=" * 80)

    parser = argparse.ArgumentParser(description="Prepare evaluation dataset")
    parser.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Path to custom CSV with Ratings/Reviews columns",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=os.path.join("evaluation", "evaluation_dataset.csv"),
        help="Output CSV path",
    )
    args = parser.parse_args()

    loader = DataLoader()
    print("\n1. Loading data...")
    if args.csv:
        df = loader.load_custom_csv(args.csv)
    else:
        df = loader.load_reviews()

    print("\n2. Filtering negative reviews...")
    negative_df = loader.filter_negative_reviews(df)

    print("\n3. Sampling 100 reviews...")
    random.seed(42)
    sampled_df = negative_df.sample(n=min(100, len(negative_df)), random_state=42)

    eval_df = pd.DataFrame(
        {
            "review_id": sampled_df["review_id"],
            "review_text": sampled_df["review_text"],
            "rating": sampled_df["rating"],
            "manual_label": "",
            "notes": "",
        }
    )

    output_file = args.output
    output_dir = os.path.dirname(output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    eval_df.to_csv(output_file, index=False, encoding="utf-8-sig")

    print("\nDone!")
    print(f"  File: {output_file}")
    print(f"  Samples: {len(eval_df)}")
    print("\nNext steps:")
    print(f"  1. Open {output_file} in Excel/Sheets")
    print("  2. Fill the 'manual_label' column")
    print("  3. Refer to evaluation/labeling_guide.md for categories")

    print("\nRating distribution:")
    print(eval_df["rating"].value_counts().sort_index())

    print("\nSample preview (first 3):")
    print("-" * 80)
    for _, row in eval_df.head(3).iterrows():
        print(f"\nID: {row['review_id']}")
        print(f"Rating: {row['rating']}")
        print(f"Text: {row['review_text'][:200]}...")
        print("-" * 80)


if __name__ == "__main__":
    main()
