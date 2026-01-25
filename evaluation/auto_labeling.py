"""
GPT-4를 사용한 자동 라벨링 스크립트
Ground Truth 생성을 위한 초기 라벨링 자동화
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import json
from openai import OpenAI
import config

CATEGORIES = [
    "battery_issue",        # 배터리 문제 (방전, 충전, 발열)
    "network_issue",        # 네트워크/신호 문제 (WiFi, 셀룰러, 핫스팟)
    "display_issue",        # 화면 문제 (크기, 품질, 결함)
    "software_issue",       # 소프트웨어 문제 (버그, 업데이트, 호환성)
    "overheating",          # 발열 문제 (배터리 외 발열)
    "sound_issue",          # 사운드/스피커 문제
    "delivery_delay",       # 배송 지연
    "wrong_item",           # 잘못된 상품
    "poor_quality",         # 품질 불량
    "damaged_packaging",    # 포장/상품 파손
    "size_issue",           # 사이즈 문제 (화면 크기 포함)
    "missing_parts",        # 부품 누락 (충전기, 이어폰 등)
    "not_as_described",     # 설명과 다름
    "customer_service",     # 고객 서비스 문제
    "price_issue",          # 가격 문제
    "positive_review",      # 긍정적 리뷰 (평점과 내용 불일치)
    "other"                 # 기타
]

def auto_label_reviews(input_file: str, output_file: str, batch_size: int = 20):
    """
    GPT-4로 리뷰 자동 라벨링

    Args:
        input_file: 입력 CSV 파일 경로
        output_file: 출력 CSV 파일 경로
        batch_size: 한 번에 처리할 리뷰 수
    """
    client = OpenAI(api_key=config.OPENAI_API_KEY)

    # 데이터 로드
    df = pd.read_csv(input_file)
    print(f"총 {len(df)}개 리뷰 로드됨")

    all_labels = []

    # 배치 단위로 처리
    for i in range(0, len(df), batch_size):
        batch_df = df.iloc[i:i+batch_size]
        batch_reviews = []

        for idx, row in batch_df.iterrows():
            batch_reviews.append({
                "index": idx,
                "review_id": row["review_id"],
                "text": row["review_text"][:500]  # 토큰 제한
            })

        print(f"\n처리 중: {i+1}~{min(i+batch_size, len(df))} / {len(df)}")

        # GPT-4 호출
        labels = call_gpt_for_labeling(client, batch_reviews)
        all_labels.extend(labels)

    # 결과 저장
    df["manual_label"] = ""
    df["confidence"] = ""
    df["reasoning"] = ""

    for label_info in all_labels:
        idx = label_info["index"]
        df.at[idx, "manual_label"] = label_info["category"]
        df.at[idx, "confidence"] = label_info.get("confidence", "")
        df.at[idx, "reasoning"] = label_info.get("reasoning", "")

    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"\n완료! 저장됨: {output_file}")

    # 카테고리 분포 출력
    print("\n카테고리 분포:")
    print(df["manual_label"].value_counts())

    return df


def call_gpt_for_labeling(client: OpenAI, reviews: list) -> list:
    """
    GPT-4에 라벨링 요청
    """
    reviews_text = "\n".join([
        f'{r["index"]}. [ID:{r["review_id"]}] {r["text"]}'
        for r in reviews
    ])

    prompt = f"""You are an expert at categorizing smartphone (iPhone) product reviews.

Categorize each review into ONE of these categories:

Categories:
- battery_issue: Battery problems (draining fast, not charging, poor backup, battery health)
- network_issue: Network/signal problems (weak WiFi, cellular, hotspot, eSIM issues)
- display_issue: Screen problems (screen defects, vibration, flickering, quality issues)
- software_issue: Software problems (bugs, updates, configuration, iOS issues, hanging)
- overheating: Device getting hot during use (not battery-related heating)
- sound_issue: Speaker/audio problems (low volume, distortion, call audio issues)
- delivery_delay: Shipping/delivery took too long
- wrong_item: Received incorrect product (wrong color, model)
- poor_quality: General product quality issues (defective, broke easily)
- damaged_packaging: Package or product arrived damaged
- size_issue: Phone size complaints (too small screen, bezels)
- missing_parts: Missing accessories (no charger, no earphones, no adapter)
- not_as_described: Product doesn't match listing/description (false advertising)
- customer_service: Service/support issues (Flipkart, Apple support, refund problems)
- price_issue: Price-related complaints (too expensive, not worth money)
- positive_review: Actually positive review despite low rating (user error in rating)
- other: Cannot be categorized or extremely vague ("bad", "worst", "hate" only)

Rules:
1. Choose the PRIMARY issue if multiple exist
2. "Battery backup" complaints = battery_issue
3. "Phone heating/hot" = overheating (unless specifically about charging)
4. "Network/signal/hotspot weak" = network_issue
5. "Screen small" = size_issue
6. If review is actually positive ("Nice phone", "Good", "Love it"), use positive_review
7. Only use "other" for extremely vague reviews with no identifiable issue

Reviews to categorize:
{reviews_text}

Output JSON format:
{{
  "labels": [
    {{
      "index": 0,
      "category": "category_name",
      "confidence": 0.9,
      "reasoning": "brief explanation"
    }},
    ...
  ]
}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # 라벨링에는 더 정확한 모델 사용
            messages=[
                {"role": "system", "content": "You are a precise review categorization expert. Output valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # 일관성을 위해 낮은 temperature
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        return result.get("labels", [])

    except Exception as e:
        print(f"API 호출 에러: {e}")
        # 에러 시 빈 라벨 반환
        return [{"index": r["index"], "category": "other", "reasoning": "API error"} for r in reviews]


def main():
    input_file = "evaluation/evalutaion_dataset.csv"  # 오타 있는 현재 파일명
    output_file = "evaluation/evaluation_dataset.csv"  # 올바른 파일명으로 저장

    if not os.path.exists(input_file):
        print(f"파일을 찾을 수 없습니다: {input_file}")
        return

    print("="*60)
    print("  GPT-4 자동 라벨링 시작")
    print("="*60)

    df = auto_label_reviews(input_file, output_file, batch_size=20)

    print("\n" + "="*60)
    print("  검수가 필요한 리뷰 (confidence < 0.8 또는 'other')")
    print("="*60)

    # 검수 필요한 케이스 추출
    needs_review = df[
        (df["manual_label"] == "other") |
        (df["confidence"].astype(str).apply(lambda x: float(x) if x else 1.0) < 0.8)
    ]

    print(f"\n검수 필요: {len(needs_review)}개")
    if len(needs_review) > 0:
        for _, row in needs_review.head(10).iterrows():
            print(f"\n[{row['review_id']}] {row['review_text'][:80]}...")
            print(f"  → 라벨: {row['manual_label']}, 이유: {row['reasoning']}")


if __name__ == "__main__":
    main()
