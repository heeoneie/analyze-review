import os
from datetime import datetime, timedelta

import kagglehub
import pandas as pd

from core import config

class DataLoader:
    def __init__(self):
        self.data_path = config.DATA_PATH
        os.makedirs(self.data_path, exist_ok=True)

    def download_dataset(self):
        """Download Olist Brazilian E-commerce dataset from Kaggle"""
        print("Downloading dataset from Kaggle...")
        path = kagglehub.dataset_download("olistbr/brazilian-ecommerce")
        print(f"Dataset downloaded to: {path}")
        return path

    def load_custom_csv(self, csv_path):
        """Load custom CSV file with reviews"""
        print(f"Loading custom CSV from: {csv_path}")

        df = pd.read_csv(csv_path)

        # Check if required columns exist
        if 'Ratings' in df.columns and 'Reviews' in df.columns:
            # Custom CSV format (like iPhone SE reviews)
            processed_df = df[['Ratings', 'Reviews']].copy()
            processed_df.rename(columns={
                'Ratings': 'rating',
                'Reviews': 'review_text'
            }, inplace=True)

            # Add synthetic review_id and created_at
            processed_df['review_id'] = range(1, len(processed_df) + 1)
            # Create synthetic dates (spread over last 60 days)
            base_date = datetime.now()
            processed_df['created_at'] = [
                base_date - timedelta(days=i % 60)
                for i in range(len(processed_df))
            ]
        else:
            raise ValueError("CSV must have 'Ratings' and 'Reviews' columns")

        # Filter out reviews without text
        processed_df = processed_df[processed_df['review_text'].notna()].copy()

        # Sort by date
        processed_df.sort_values('created_at', ascending=False, inplace=True)
        processed_df.reset_index(drop=True, inplace=True)

        print(f"\nLoaded {len(processed_df)} reviews with text")
        print(f"Rating distribution:\n{processed_df['rating'].value_counts().sort_index()}")

        return processed_df

    def load_reviews(self, dataset_path=None):
        """Load and merge review data with necessary information"""
        if dataset_path is None:
            dataset_path = self.download_dataset()

        # Load reviews
        reviews_df = pd.read_csv(os.path.join(dataset_path, "olist_order_reviews_dataset.csv"))

        # Load orders to get timestamp information
        orders_df = pd.read_csv(os.path.join(dataset_path, "olist_orders_dataset.csv"))

        # Merge reviews with orders to get order_purchase_timestamp
        merged_df = reviews_df.merge(
            orders_df[['order_id', 'order_purchase_timestamp']],
            on='order_id',
            how='left'
        )

        # Rename and select columns
        processed_df = merged_df[[
            'review_id',
            'review_comment_message',
            'review_score',
            'order_purchase_timestamp'
        ]].copy()

        processed_df.rename(columns={
            'review_comment_message': 'review_text',
            'review_score': 'rating',
            'order_purchase_timestamp': 'created_at'
        }, inplace=True)

        # Convert timestamp to datetime
        processed_df['created_at'] = pd.to_datetime(processed_df['created_at'])

        # Filter out reviews without text
        processed_df = processed_df[processed_df['review_text'].notna()].copy()

        # Sort by date
        processed_df.sort_values('created_at', ascending=False, inplace=True)
        processed_df.reset_index(drop=True, inplace=True)

        print(f"\nLoaded {len(processed_df)} reviews with text")
        print(
            f"Date range: {processed_df['created_at'].min()} to "
            f"{processed_df['created_at'].max()}"
        )
        print(f"Rating distribution:\n{processed_df['rating'].value_counts().sort_index()}")

        return processed_df

    def filter_negative_reviews(self, df, threshold=None):
        """Filter negative reviews based on rating threshold"""
        if threshold is None:
            threshold = config.NEGATIVE_RATING_THRESHOLD

        negative_df = df[df['rating'] <= threshold].copy()
        print(f"\nFiltered {len(negative_df)} negative reviews (rating <= {threshold})")

        return negative_df

    def split_by_period(self, df, recent_days=None, comparison_days=None):
        """Split data into recent and comparison periods"""
        if recent_days is None:
            recent_days = config.RECENT_PERIOD_DAYS
        if comparison_days is None:
            comparison_days = config.COMPARISON_PERIOD_DAYS

        # Get the most recent date in the dataset
        max_date = df['created_at'].max()

        # Define periods
        recent_start = max_date - timedelta(days=recent_days)
        comparison_start = max_date - timedelta(days=comparison_days)

        recent_df = df[df['created_at'] >= recent_start].copy()
        comparison_df = df[
            (df['created_at'] >= comparison_start) &
            (df['created_at'] < recent_start)
        ].copy()

        print(f"\nRecent period ({recent_days} days): {len(recent_df)} reviews")
        print(
            f"Comparison period ({comparison_days - recent_days} days): "
            f"{len(comparison_df)} reviews"
        )

        return recent_df, comparison_df
