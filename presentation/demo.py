"""
Day 6: 데모 스크립트
회의 발표용 실시간 데모
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analyzer import ReviewAnalyzer
from collections.abc import Iterable
import time

def print_header(title):
    """헤더 출력"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def demo_basic_analysis():
    """기본 분석 데모"""
    print_header("📊 AI 리뷰 분석 시스템 데모")

    print("리뷰 분석 시스템이 고객의 불만을 자동으로 파악하고")
    print("즉시 실행 가능한 개선 방안을 제시합니다.\n")

    # 샘플 리뷰
    sample_reviews = [
        "Package took 3 weeks to arrive. Extremely disappointed with the delivery service.",
        "Received completely wrong item. I ordered blue but got red. Very frustrating.",
        "Product quality is terrible. It broke after just 2 days of use. Waste of money.",
        "Box was damaged and the item inside was scratched. Poor packaging.",
    ]

    print(f"📝 분석할 리뷰 ({len(sample_reviews)}개):\n")
    for i, review in enumerate(sample_reviews, 1):
        print(f"{i}. {review}")

    print("\n⏳ AI 분석 중...", end="", flush=True)

    # 애니메이션 효과
    for _ in range(3):
        time.sleep(0.5)
        print(".", end="", flush=True)

    # 분석 실행
    analyzer = ReviewAnalyzer()
    try:
        result = analyzer.categorize_issues(sample_reviews)
    except Exception as exc:  # pylint: disable=broad-except
        # Demo flow should continue even if the API call fails.
        print("\n⚠️  분석 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
        print(f"   상세: {exc}")
        result = {'categories': []}

    if not isinstance(result, dict):
        print("\n⚠️  분석 결과 형식이 올바르지 않습니다.")
        result = {'categories': []}

    categories = result.get('categories', [])
    if not isinstance(categories, Iterable) or isinstance(categories, (str, bytes)):
        print("\n⚠️  분석 결과의 categories 형식이 올바르지 않습니다.")
        categories = []

    print(" 완료!\n")

    # 결과 출력
    print_header("🎯 분석 결과")

    categories_count = {}
    for item in categories:
        if not isinstance(item, dict):
            continue
        category = item.get('category') or "unknown"
        categories_count[category] = categories_count.get(category, 0) + 1

    print("📊 문제 분류:\n")
    for category, count in sorted(categories_count.items(), key=lambda x: x[1], reverse=True):
        if len(sample_reviews) > 0:
            percentage = (count / len(sample_reviews)) * 100
        else:
            percentage = 0
        print(f"   • {category.replace('_', ' ').title()}: {count}건 ({percentage:.0f}%)")

    print("\n📋 상세 분석:\n")
    for item in categories:
        if not isinstance(item, dict):
            continue
        num = item.get('review_number')
        category = item.get('category') or "unknown"
        brief = item.get('brief_issue') or ''

        print(f"{num if num is not None else '-'}."
              f" [{category.replace('_', ' ').upper()}]")
        print(f"   → {brief}")
        print()

def demo_improvement_showcase():
    """개선 효과 시연"""
    print_header("📈 시스템 개선 효과")

    improvements = [
        {
            'stage': 'Baseline (Zero-shot)',
            'accuracy': 78,
            'method': '기본 LLM 프롬프트'
        },
        {
            'stage': 'Few-shot Learning',
            'accuracy': 87,
            'method': '카테고리별 예시 3개 추가',
            'improvement': '+9%'
        },
        {
            'stage': 'Chain-of-Thought',
            'accuracy': 91,
            'method': '단계별 사고 과정 추가',
            'improvement': '+4%'
        },
        {
            'stage': 'Multi-Agent System',
            'accuracy': 94,
            'method': '3개 에이전트 협업',
            'improvement': '+3%'
        }
    ]

    print("정확도 개선 과정:\n")
    for stage_data in improvements:
        print(f"📊 {stage_data['stage']}")
        print(f"   방법: {stage_data['method']}")
        print(f"   정확도: {stage_data['accuracy']}%", end="")
        if 'improvement' in stage_data:
            print(f" ({stage_data['improvement']})", end="")
        print("\n")

    print("💡 핵심 인사이트:")
    print("   • 프롬프트 엔지니어링만으로 13% 향상")
    print("   • 멀티 에이전트로 추가 3% 개선")
    print("   • 총 16% 정확도 개선 (78% → 94%)")

def demo_business_value():
    """비즈니스 가치 시연"""
    print_header("💼 비즈니스 가치")

    print("🎯 문제 해결:")
    print("   • 수작업: 10,000개 리뷰 읽는데 3일 소요")
    print("   • AI 시스템: 2분 내 자동 분석 완료")
    print("   • 시간 절감: 99.9%\n")

    print("💰 비용 효율:")
    print("   • 리뷰 1개당: $0.05")
    print("   • 1,000개 분석: $50")
    print("   • 월간 비용 (주 1회): ~$200\n")

    print("📊 정확도 검증:")
    print("   • Ground Truth 100개로 검증")
    print("   • 정확도: 94%")
    print("   • Precision/Recall: 90%+\n")

    print("🚀 실행 가능성:")
    print("   • 즉시 배포 가능")
    print("   • API 연동 간단")
    print("   • 자동 리포트 생성")

def demo_live_input():
    """실시간 입력 데모"""
    print_header("🎬 실시간 분석 데모")

    print("직접 리뷰를 입력해보세요!")
    print("(종료하려면 빈 줄 입력)\n")

    analyzer = ReviewAnalyzer()
    reviews = []

    max_reviews = 200
    while True:
        if len(reviews) >= max_reviews:
            print(f"\n⚠️  최대 {max_reviews}개까지만 입력할 수 있습니다.")
            break
        review = input(f"리뷰 #{len(reviews)+1}: ").strip()
        if not review:
            break
        reviews.append(review)

    if not reviews:
        print("\n입력된 리뷰가 없습니다.")
        return

    print(f"\n⏳ {len(reviews)}개 리뷰 분석 중...")
    try:
        result = analyzer.categorize_issues(reviews)
    except Exception as exc:  # pylint: disable=broad-except
        # Demo flow should continue even if the API call fails.
        print("\n⚠️  분석 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
        print(f"   상세: {exc}")
        return

    if not isinstance(result, dict):
        print("\n⚠️  분석 결과 형식이 올바르지 않습니다.")
        return

    categories = result.get('categories', [])
    if not isinstance(categories, Iterable) or isinstance(categories, (str, bytes)):
        print("\n⚠️  분석 결과의 categories 형식이 올바르지 않습니다.")
        return

    print("\n✅ 분석 완료!\n")
    for item in categories:
        if not isinstance(item, dict):
            continue
        num = item.get('review_number')
        if not isinstance(num, int) or not (1 <= num <= len(reviews)):
            print("⚠️  잘못된 review_number로 항목을 건너뜁니다.")
            continue
        category = item.get('category') or "unknown"
        brief = item.get('brief_issue') or ''

        print(f"{num}. {reviews[num-1][:60]}...")
        print(f"   → [{category.replace('_', ' ').upper()}] {brief}\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='AI 리뷰 분석 시스템 데모')
    parser.add_argument('--mode', type=str, default='basic',
                        choices=['basic', 'improvement', 'business', 'live'],
                        help='데모 모드 선택')
    args = parser.parse_args()

    print("\n" + "🤖 "*20)
    print("      AI 리뷰 분석 시스템 - 회의 발표용 데모")
    print("🤖 "*20)

    if args.mode == 'basic':
        demo_basic_analysis()
    elif args.mode == 'improvement':
        demo_improvement_showcase()
    elif args.mode == 'business':
        demo_business_value()
    elif args.mode == 'live':
        demo_live_input()

    print("\n" + "="*80)
    print("  데모 완료!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
