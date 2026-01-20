"""
Day 6: 실험 결과 시각화
정확도 개선, Confusion Matrix, 비용 분석 등 차트 생성
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from glob import glob

# 한글 폰트 설정 (Mac)
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

class ResultsVisualizer:
    def __init__(self, results_dir='results'):
        self.results_dir = results_dir
        self.output_dir = os.path.join(results_dir, 'figures')
        os.makedirs(self.output_dir, exist_ok=True)

    def load_experiment_results(self):
        """실험 결과 파일들 로드"""
        results = {}

        # 메트릭스 파일들 찾기
        metric_files = glob(os.path.join(self.results_dir, '*_metrics_*.json'))

        for file_path in metric_files:
            # 파일명에서 실험 타입 추출
            filename = os.path.basename(file_path)
            if 'baseline' in filename:
                exp_type = 'baseline'
            elif 'improved' in filename:
                exp_type = 'improved'
            elif 'final' in filename:
                exp_type = 'final'
            else:
                continue

            with open(file_path, 'r', encoding='utf-8') as f:
                results[exp_type] = json.load(f)

        # 프롬프트 실험 결과
        prompt_files = glob(os.path.join(self.results_dir, 'prompt_experiments_*.json'))
        if prompt_files:
            with open(prompt_files[0], 'r', encoding='utf-8') as f:
                results['prompt_experiments'] = json.load(f)

        return results

    def plot_accuracy_improvement(self, results):
        """정확도 개선 추이 라인 차트"""
        print("\n📊 정확도 개선 차트 생성 중...")

        # 데이터 준비
        stages = []
        accuracies = []

        # Baseline
        if 'baseline' in results:
            stages.append('Baseline\n(Zero-shot)')
            accuracies.append(results['baseline']['accuracy'] * 100)

        # Prompt Experiments
        if 'prompt_experiments' in results:
            prompt_results = results['prompt_experiments']
            if 'few_shot_3' in prompt_results:
                stages.append('Few-shot\n(3-shot)')
                accuracies.append(prompt_results['few_shot_3']['accuracy'] * 100)

            if 'cot' in prompt_results:
                stages.append('Few-shot\n+ CoT')
                accuracies.append(prompt_results['cot']['accuracy'] * 100)

        # Improved
        if 'improved' in results:
            stages.append('Improved\n(Optimized)')
            accuracies.append(results['improved']['accuracy'] * 100)

        # Final
        if 'final' in results:
            stages.append('Final\n(Multi-Agent)')
            accuracies.append(results['final']['accuracy'] * 100)

        # 플롯 생성
        plt.figure(figsize=(12, 6))
        plt.plot(stages, accuracies, marker='o', linewidth=2, markersize=10)

        # 각 포인트에 수치 표시
        for i, (stage, acc) in enumerate(zip(stages, accuracies)):
            plt.text(i, acc + 1, f'{acc:.1f}%', ha='center', va='bottom', fontsize=12, fontweight='bold')

        plt.title('정확도 개선 추이', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Stage', fontsize=12)
        plt.ylabel('Accuracy (%)', fontsize=12)
        plt.ylim(70, 100)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        output_path = os.path.join(self.output_dir, 'accuracy_improvement.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"   ✓ 저장: {output_path}")

    def plot_method_comparison(self, results):
        """방법론 비교 막대 그래프"""
        print("\n📊 방법론 비교 차트 생성 중...")

        if 'prompt_experiments' not in results:
            print("   ⚠️  프롬프트 실험 결과 없음")
            return

        prompt_results = results['prompt_experiments']

        # 데이터 준비
        methods = []
        accuracies = []
        colors = []

        baseline_acc = None
        if 'zero_shot' in prompt_results:
            baseline_acc = prompt_results['zero_shot']['accuracy'] * 100

        for method, data in prompt_results.items():
            # 온도 실험 제외
            if 'temperature' in method:
                continue

            label = method.replace('_', ' ').title()
            acc = data['accuracy'] * 100

            methods.append(label)
            accuracies.append(acc)

            # 베이스라인보다 높으면 녹색, 낮으면 빨간색
            if baseline_acc is not None and acc >= baseline_acc:
                colors.append('green')
            else:
                colors.append('red')

        # 플롯 생성
        plt.figure(figsize=(10, 6))
        bars = plt.barh(methods, accuracies, color=colors, alpha=0.7)

        # 수치 표시
        for bar, acc in zip(bars, accuracies):
            plt.text(acc + 0.5, bar.get_y() + bar.get_height()/2,
                     f'{acc:.1f}%', va='center', fontsize=11, fontweight='bold')

        plt.title('프롬프트 엔지니어링 방법론 비교', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Accuracy (%)', fontsize=12)
        plt.xlim(70, 100)
        plt.grid(True, axis='x', alpha=0.3)
        plt.tight_layout()

        output_path = os.path.join(self.output_dir, 'method_comparison.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"   ✓ 저장: {output_path}")

    def plot_per_class_performance(self, results):
        """카테고리별 성능 히트맵"""
        print("\n📊 카테고리별 성능 차트 생성 중...")

        # 가장 최근 결과 사용
        if 'final' in results:
            data = results['final']
        elif 'improved' in results:
            data = results['improved']
        elif 'baseline' in results:
            data = results['baseline']
        else:
            print("   ⚠️  평가 결과 없음")
            return

        if 'per_class_metrics' not in data:
            print("   ⚠️  카테고리별 메트릭스 없음")
            return

        # 데이터 준비
        categories = list(data['per_class_metrics'].keys())
        precision = [data['per_class_metrics'][cat]['precision'] * 100 for cat in categories]
        recall = [data['per_class_metrics'][cat]['recall'] * 100 for cat in categories]
        f1 = [data['per_class_metrics'][cat]['f1'] * 100 for cat in categories]

        # 데이터프레임 생성
        df = pd.DataFrame({
            'Precision': precision,
            'Recall': recall,
            'F1 Score': f1
        }, index=categories)

        # 플롯 생성
        plt.figure(figsize=(12, len(categories) * 0.5 + 2))
        sns.heatmap(df.T, annot=True, fmt='.1f', cmap='YlGnBu',
                    cbar_kws={'label': 'Score (%)'}, vmin=0, vmax=100)

        plt.title('카테고리별 성능 (Precision, Recall, F1)', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Category', fontsize=12)
        plt.ylabel('Metric', fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        output_path = os.path.join(self.output_dir, 'per_class_performance.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"   ✓ 저장: {output_path}")

    def plot_cost_accuracy_tradeoff(self, results):
        """비용 vs 정확도 산점도"""
        print("\n📊 비용-정확도 트레이드오프 차트 생성 중...")

        # 예상 비용 (상대적)
        cost_map = {
            'baseline': 1.0,
            'few_shot_3': 1.5,
            'cot': 2.0,
            'improved': 1.8,
            'final': 3.0  # Multi-agent
        }

        stages = []
        accuracies = []
        costs = []

        if 'baseline' in results:
            stages.append('Baseline')
            accuracies.append(results['baseline']['accuracy'] * 100)
            costs.append(cost_map['baseline'])

        if 'prompt_experiments' in results:
            prompt_results = results['prompt_experiments']
            if 'few_shot_3' in prompt_results:
                stages.append('Few-shot')
                accuracies.append(prompt_results['few_shot_3']['accuracy'] * 100)
                costs.append(cost_map['few_shot_3'])
            if 'cot' in prompt_results:
                stages.append('CoT')
                accuracies.append(prompt_results['cot']['accuracy'] * 100)
                costs.append(cost_map['cot'])

        if 'improved' in results:
            stages.append('Improved')
            accuracies.append(results['improved']['accuracy'] * 100)
            costs.append(cost_map['improved'])

        if 'final' in results:
            stages.append('Multi-Agent')
            accuracies.append(results['final']['accuracy'] * 100)
            costs.append(cost_map['final'])

        # 플롯 생성
        plt.figure(figsize=(10, 6))
        plt.scatter(costs, accuracies, s=200, alpha=0.6, c=range(len(stages)), cmap='viridis')

        # 라벨 표시
        for i, (cost, acc, stage) in enumerate(zip(costs, accuracies, stages)):
            plt.annotate(stage, (cost, acc), xytext=(10, -5),
                        textcoords='offset points', fontsize=11, fontweight='bold')

        plt.title('비용 vs 정확도 트레이드오프', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('상대적 비용 (Baseline = 1.0)', fontsize=12)
        plt.ylabel('Accuracy (%)', fontsize=12)
        plt.xlim(0.5, 3.5)
        plt.ylim(70, 100)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        output_path = os.path.join(self.output_dir, 'cost_accuracy_tradeoff.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"   ✓ 저장: {output_path}")

    def create_summary_report(self, results):
        """요약 리포트 생성"""
        print("\n📄 요약 리포트 생성 중...")

        report_lines = []
        report_lines.append("# 실험 결과 요약 리포트\n")
        report_lines.append(f"생성 날짜: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        report_lines.append("## 정확도 개선\n\n")
        report_lines.append("| Stage | Accuracy | Improvement |\n")
        report_lines.append("|-------|----------|-------------|\n")

        baseline_acc = None
        if 'baseline' in results:
            baseline_acc = results['baseline']['accuracy']
            report_lines.append(f"| Baseline | {baseline_acc*100:.2f}% | - |\n")

        if 'prompt_experiments' in results:
            prompt_results = results['prompt_experiments']
            for method, data in prompt_results.items():
                if 'temperature' in method:
                    continue
                acc = data['accuracy']
                improvement = (acc - baseline_acc) * 100 if baseline_acc else 0
                method_name = method.replace('_', ' ').title()
                report_lines.append(f"| {method_name} | {acc*100:.2f}% | +{improvement:.1f}% |\n")

        if 'final' in results:
            final_acc = results['final']['accuracy']
            improvement = (final_acc - baseline_acc) * 100 if baseline_acc else 0
            report_lines.append(f"| Final | {final_acc*100:.2f}% | +{improvement:.1f}% |\n")

        report_lines.append("\n## 생성된 차트\n\n")
        report_lines.append("- accuracy_improvement.png: 정확도 개선 추이\n")
        report_lines.append("- method_comparison.png: 방법론 비교\n")
        report_lines.append("- per_class_performance.png: 카테고리별 성능\n")
        report_lines.append("- cost_accuracy_tradeoff.png: 비용-정확도 트레이드오프\n")

        output_path = os.path.join(self.output_dir, 'summary_report.md')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(report_lines)

        print(f"   ✓ 저장: {output_path}")

    def generate_all_charts(self):
        """모든 차트 생성"""
        print("="*80)
        print("  실험 결과 시각화")
        print("="*80)

        # 결과 로드
        print("\n📂 결과 파일 로딩...")
        results = self.load_experiment_results()

        if not results:
            print("\n⚠️  결과 파일을 찾을 수 없습니다.")
            print(f"   {self.results_dir} 디렉토리를 확인하세요.")
            return

        print(f"   ✓ {len(results)}개 결과 파일 로드됨")

        # 차트 생성
        self.plot_accuracy_improvement(results)
        self.plot_method_comparison(results)
        self.plot_per_class_performance(results)
        self.plot_cost_accuracy_tradeoff(results)

        # 요약 리포트
        self.create_summary_report(results)

        print("\n" + "="*80)
        print(f"  ✓ 모든 차트 생성 완료!")
        print(f"  저장 위치: {self.output_dir}")
        print("="*80)


def main():
    visualizer = ResultsVisualizer()
    visualizer.generate_all_charts()


if __name__ == "__main__":
    main()
