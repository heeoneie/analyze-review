"""
Level 3: 에러 분석 & 개선
틀린 케이스를 분석하여 패턴을 찾고 프롬프트 개선
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import json
from collections import Counter, defaultdict
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

class ErrorAnalyzer:
    def __init__(self, evaluation_results_file):
        """
        Args:
            evaluation_results_file: evaluate.py 실행 결과 파일 경로
        """
        self.results_file = evaluation_results_file
        self.errors = []
        self.ground_truth_df = None

    def load_evaluation_results(self):
        """평가 결과 로드"""
        with open(self.results_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 에러 케이스 파일 찾기
        error_file = None
        if '_metrics_' in self.results_file:
            error_file = self.results_file.replace('_metrics_', '_errors_')
        elif self.results_file.endswith('_metrics.json'):
            error_file = self.results_file.replace('_metrics.json', '_errors.json')

        if error_file and os.path.exists(error_file):
            with open(error_file, 'r', encoding='utf-8') as f:
                self.errors = json.load(f)

        return data

    def analyze_confusion_pairs(self):
        """자주 혼동되는 카테고리 쌍 분석"""
        print("\n" + "="*80)
        print("  1. 혼동 카테고리 쌍 분석")
        print("="*80)

        confusion_pairs = Counter()

        for error in self.errors:
            true_label = error['true_label']
            pred_label = error['predicted_label']
            pair = tuple(sorted([true_label, pred_label]))
            confusion_pairs[pair] += 1

        print("\n가장 많이 혼동되는 카테고리 쌍 (Top 5):\n")
        print("{:<25} {:<25} {:<10}".format("True Label", "Predicted Label", "Count"))
        print("-" * 80)

        for (label1, label2), count in confusion_pairs.most_common(5):
            print(f"{label1:<25} ↔ {label2:<25} {count:<10}")

        return confusion_pairs

    def analyze_error_patterns(self):
        """에러 패턴 분석"""
        print("\n" + "="*80)
        print("  2. 에러 패턴 분석")
        print("="*80)

        patterns = {
            'review_length': defaultdict(int),
            'rating': defaultdict(int),
            'categories': defaultdict(int)
        }

        for error in self.errors:
            # 리뷰 길이별 에러
            text_length = len(error['review_text'])
            if text_length < 50:
                length_category = 'very_short'
            elif text_length < 150:
                length_category = 'short'
            elif text_length < 300:
                length_category = 'medium'
            else:
                length_category = 'long'

            patterns['review_length'][length_category] += 1

            # 평점별 에러
            if 'rating' in error:
                patterns['rating'][str(error['rating'])] += 1

            # 카테고리별 에러 발생 빈도
            patterns['categories'][error['true_label']] += 1

        # 리뷰 길이별 에러
        print("\n📏 리뷰 길이별 에러 분포:")
        for length, count in sorted(patterns['review_length'].items()):
            print(f"   {length:>12}: {count:>3}건")

        # 평점별 에러
        if patterns['rating']:
            print("\n⭐ 평점별 에러 분포:")
            for rating, count in sorted(patterns['rating'].items()):
                print(f"   {rating}점: {count:>3}건")

        # 카테고리별 에러
        print("\n🏷️  카테고리별 에러 발생 (Top 5):")
        for category, count in Counter(patterns['categories']).most_common(5):
            print(f"   {category:<25}: {count:>3}건")

        return patterns

    def identify_common_keywords(self):
        """에러 케이스의 공통 키워드 분석"""
        print("\n" + "="*80)
        print("  3. 에러 케이스 공통 키워드")
        print("="*80)

        # Stopwords 정의
        stopwords = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
            'ought', 'used', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
            'from', 'as', 'into', 'through', 'during', 'before', 'after', 'above',
            'below', 'between', 'under', 'again', 'further', 'then', 'once',
            'here', 'there', 'when', 'where', 'why', 'how', 'all', 'each', 'few',
            'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only',
            'own', 'same', 'so', 'than', 'too', 'very', 'just', 'and', 'but',
            'if', 'or', 'because', 'until', 'while', 'this', 'that', 'these',
            'those', 'am', 'it', 'its', 'i', 'me', 'my', 'myself', 'we', 'our',
            'you', 'your', 'he', 'him', 'his', 'she', 'her', 'they', 'them',
            'what', 'which', 'who', 'whom', 'also', 'get', 'got', 'like', 'even'
        }

        # 혼동 쌍별로 공통 키워드 찾기
        confusion_keywords = defaultdict(list)
        confusion_top_keywords = {}

        for error in self.errors:
            key = f"{error['true_label']} → {error['predicted_label']}"
            confusion_keywords[key].append(error['review_text'])

        # 상위 3개 혼동 쌍만 분석
        top_confusions = Counter()
        for error in self.errors:
            key = f"{error['true_label']} → {error['predicted_label']}"
            top_confusions[key] += 1

        print("\n주요 혼동 케이스의 특징:")
        for confusion, count in top_confusions.most_common(3):
            print(f"\n{confusion} ({count}건):")
            reviews = confusion_keywords[confusion]

            # 토큰화 및 정규화
            all_tokens = []
            for review in reviews:
                # 소문자로 변환, 알파벳만 추출
                tokens = review.lower().split()
                # 특수문자 제거 및 필터링
                cleaned_tokens = []
                for tok in tokens:
                    clean_tok = ''.join(c for c in tok if c.isalpha())
                    # 길이 2 이상, stopword 아닌 것만
                    if len(clean_tok) >= 2 and clean_tok not in stopwords:
                        cleaned_tokens.append(clean_tok)
                all_tokens.extend(cleaned_tokens)

            # 상위 10개 키워드 추출
            top_keywords = [w for w, _ in Counter(all_tokens).most_common(10)]
            confusion_top_keywords[confusion] = top_keywords
            print(f"   키워드: {', '.join(top_keywords[:5])}")

            # 짧은 예시 3개만
            for i, review in enumerate(reviews[:3], 1):
                print(f"   {i}. {review[:100]}...")

        return {"examples": dict(confusion_keywords), "keywords": confusion_top_keywords}

    def suggest_improvements(self, confusion_pairs, patterns):
        """개선 방안 제안"""
        print("\n" + "="*80)
        print("  4. 개선 방안 제안")
        print("="*80)

        suggestions = []

        # 1. 혼동 쌍 기반 제안
        top_confusion = confusion_pairs.most_common(1)[0]
        if top_confusion:
            pair, count = top_confusion
            suggestion = {
                'issue': f"'{pair[0]}' 와 '{pair[1]}' 혼동 ({count}건)",
                'solution': "프롬프트에 두 카테고리의 명확한 차이점을 예시와 함께 추가",
                'example': f"- '{pair[0]}': [구체적 예시]\n- '{pair[1]}': [구체적 예시]"
            }
            suggestions.append(suggestion)

        # 2. 리뷰 길이 기반 제안
        if 'very_short' in patterns['review_length']:
            count = patterns['review_length']['very_short']
            if count > len(self.errors) * 0.2:  # 20% 이상
                suggestion = {
                    'issue': f"짧은 리뷰(<50자)에서 에러 많음 ({count}건)",
                    'solution': "짧은 리뷰에 대한 특별 처리 추가",
                    'example': "- 정보가 부족한 경우 'other' 카테고리 사용\n- 맥락 추론 최소화"
                }
                suggestions.append(suggestion)

        # 3. 특정 카테고리 에러 많음
        category_errors = Counter(patterns['categories'])
        if category_errors:
            top_error_category, count = category_errors.most_common(1)[0]
            if count > len(self.errors) * 0.15:  # 15% 이상
                suggestion = {
                    'issue': f"'{top_error_category}' 카테고리에서 에러 많음 ({count}건)",
                    'solution': f"'{top_error_category}' 정의를 명확히 하고 Few-shot 예시 추가",
                    'example': "해당 카테고리의 대표적인 3-5개 예시를 프롬프트에 포함"
                }
                suggestions.append(suggestion)

        # 출력
        print("\n💡 추천 개선 사항:\n")
        for i, sug in enumerate(suggestions, 1):
            print(f"{i}. 문제: {sug['issue']}")
            print(f"   해결: {sug['solution']}")
            print(f"   예시:\n   {sug['example']}")
            print()

        return suggestions

    def create_error_report(self):
        """에러 분석 리포트 생성"""
        os.makedirs('results', exist_ok=True)

        if not self.errors:
            print("\n⚠️  에러 케이스가 없습니다. 평가를 먼저 실행하세요.")
            return

        print("="*80)
        print(f"  에러 분석 리포트 (총 {len(self.errors)}건)")
        print("="*80)

        # 분석 실행
        confusion_pairs = self.analyze_confusion_pairs()
        patterns = self.analyze_error_patterns()
        keywords = self.identify_common_keywords()
        suggestions = self.suggest_improvements(confusion_pairs, patterns)

        # 결과 저장
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        confusion_pairs_serialized = [
            {"label_a": a, "label_b": b, "count": count}
            for (a, b), count in confusion_pairs.most_common()
        ]
        report = {
            'total_errors': len(self.errors),
            'confusion_pairs': confusion_pairs_serialized,
            'keywords': keywords,
            'patterns': {
                'review_length': dict(patterns['review_length']),
                'rating': dict(patterns['rating']),
                'categories': dict(patterns['categories'])
            },
            'suggestions': suggestions,
            'timestamp': timestamp
        }

        output_file = f'results/error_analysis_{timestamp}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print("\n" + "="*80)
        print(f"  리포트 저장: {output_file}")
        print("="*80)

        return report


def main():
    import argparse

    parser = argparse.ArgumentParser(description='에러 케이스 분석')
    parser.add_argument('--results', type=str,
                        help='평가 결과 파일 경로 (예: results/baseline_metrics_xxx.json)')
    args = parser.parse_args()

    if args.results:
        results_file = args.results
        if not os.path.exists(results_file):
            print("\n❌ 지정한 결과 파일을 찾을 수 없습니다.")
            print(f"경로: {results_file}")
            return
    else:
        # 가장 최근 결과 파일 자동 찾기
        results_dir = 'results'
        if os.path.exists(results_dir):
            metric_files = [
                f for f in os.listdir(results_dir)
                if f.endswith('.json') and '_metrics' in f
            ]
            if metric_files:
                # 가장 최근 파일
                metric_files.sort(reverse=True)
                results_file = os.path.join(results_dir, metric_files[0])
                print(f"\n📂 사용할 결과 파일: {results_file}\n")
            else:
                print("\n❌ 평가 결과 파일을 찾을 수 없습니다.")
                print("먼저 evaluation/evaluate.py를 실행하세요.")
                return
        else:
            print("\n❌ results 디렉토리가 없습니다.")
            print("먼저 evaluation/evaluate.py를 실행하세요.")
            return

    analyzer = ErrorAnalyzer(results_file)
    analyzer.load_evaluation_results()
    analyzer.create_error_report()


if __name__ == "__main__":
    main()
