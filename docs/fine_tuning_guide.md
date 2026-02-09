# Fine-tuning Guide

OpenAI GPT-4o-mini 모델을 Fine-tuning하여 리뷰 분류 성능을 극대화합니다.

## 왜 Fine-tuning인가?

### 장점
- **정확도 향상**: 도메인 특화 학습으로 5-10% 추가 개선 가능
- **프롬프트 단순화**: 복잡한 Few-shot 프롬프트 불필요
- **일관성 증가**: 동일 입력에 대해 더 일관된 출력
- **응답 속도**: 프롬프트가 짧아져 응답 속도 향상

### 비용
- **학습 비용**: 약 $5-10 (1회, 100-500개 샘플)
- **추론 비용**: Base 모델과 유사 ($0.03/1k tokens)
- **ROI**: 정확도 향상과 프롬프트 단순화로 충분히 가치 있음

---

## Step 1: 학습 데이터 준비

### 1-1. Ground Truth 확인
```bash
# 최소 100개 이상 라벨링된 데이터 필요
# 권장: 500개 이상
cat evaluation/evaluation_dataset.csv | wc -l
```

### 1-2. 학습 데이터 생성
```bash
python3 fine_tuning/prepare_training_data.py \
  --ground-truth evaluation/evaluation_dataset.csv \
  --output fine_tuning
```

출력:
- `fine_tuning/training_data.jsonl` (80%)
- `fine_tuning/validation_data.jsonl` (20%)

### 1-3. 데이터 포맷 검증
```bash
# OpenAI 형식 확인
head -1 fine_tuning/training_data.jsonl | jq .
```

예상 출력:
```json
{
  "messages": [
    {"role": "system", "content": "You are an expert..."},
    {"role": "user", "content": "Categorize this review: ..."},
    {"role": "assistant", "content": "delivery_delay"}
  ]
}
```

---

## Step 2: Fine-tuning 실행

### 2-1. OpenAI CLI 설치
```bash
pip install --upgrade openai
```

### 2-2. API 키 설정
```bash
export OPENAI_API_KEY="your-api-key-here"
```

### 2-3. Fine-tuning Job 시작
```bash
openai api fine_tuning.jobs.create \
  -t fine_tuning/training_data.jsonl \
  -v fine_tuning/validation_data.jsonl \
  -m gpt-4o-mini-2024-07-18 \
  --suffix "review-classifier"
```

### 2-4. 진행 상황 확인
```bash
# Job 목록 보기
openai api fine_tuning.jobs.list

# 특정 Job 상태 확인
openai api fine_tuning.jobs.get -i ftjob-xxx

# 로그 스트리밍
openai api fine_tuning.jobs.follow -i ftjob-xxx
```

### 2-5. 완료 대기
- 100개 샘플: ~10-20분
- 500개 샘플: ~30-60분
- 이메일로 완료 알림 수신

---

## Step 3: Fine-tuned 모델 평가

### 3-1. 모델 이름 확인
Fine-tuning 완료 후 모델 이름을 받게 됩니다:
```
ft:gpt-4o-mini:custom:review-classifier:AbCdEfGh
```

### 3-2. 평가 실행
```bash
python3 fine_tuning/evaluate_finetuned.py \
  --model ft:gpt-4o-mini:custom:review-classifier:AbCdEfGh \
  --ground-truth evaluation/evaluation_dataset.csv
```

### 3-3. Base 모델과 비교
```bash
python3 fine_tuning/evaluate_finetuned.py \
  --model ft:gpt-4o-mini:custom:review-classifier:AbCdEfGh \
  --ground-truth evaluation/evaluation_dataset.csv \
  --compare results/baseline_metrics.json
```

출력 예시:
```
Metric          Base Model      Fine-tuned      Improvement
------------------------------------------------------------------------
Accuracy        88.00%          95.00%          +7.00%
Precision       87.50%          94.80%          +7.30%
Recall          88.20%          95.10%          +6.90%
F1              87.80%          94.90%          +7.10%
```

---

## Step 4: Fine-tuned 모델 사용

### 4-1. analyzer.py 수정
```python
# analyzer.py
class ReviewAnalyzer:
    def __init__(self, use_finetuned=False, finetuned_model=None):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)

        if use_finetuned and finetuned_model:
            self.model = finetuned_model  # ft:gpt-4o-mini:...
        else:
            self.model = config.LLM_MODEL  # gpt-4o-mini

    def categorize_issues(self, reviews_text_list):
        # 기존 로직 유지
        # self.model이 fine-tuned 모델이면 자동으로 사용됨
        ...
```

### 4-2. 실행
```python
from analyzer import ReviewAnalyzer

# Fine-tuned 모델 사용
analyzer = ReviewAnalyzer(
    use_finetuned=True,
    finetuned_model="ft:gpt-4o-mini:custom:review-classifier:AbCdEfGh"
)

result = analyzer.categorize_issues(reviews)
```

---

## Troubleshooting

### 문제 1: "Insufficient training data"
**원인**: 학습 데이터가 너무 적음 (< 10개)

**해결**:
- 최소 100개 이상 준비
- 권장: 500개 이상

### 문제 2: Validation loss가 감소하지 않음
**원인**: 데이터 품질 문제 또는 과적합

**해결**:
- 라벨링 일관성 재검토
- 데이터 추가 수집
- Epoch 수 조정

### 문제 3: Fine-tuned 모델이 Base보다 성능이 낮음
**원인**: 데이터가 편향되었거나 품질이 낮음

**해결**:
- 카테고리별 샘플 수 균형 맞추기
- 라벨링 재검토
- 더 많은 데이터 추가

---

## Best Practices

### 데이터 품질
1. **라벨링 일관성**: 같은 기준으로 분류
2. **카테고리 균형**: 각 카테고리 최소 10개 이상
3. **데이터 다양성**: 다양한 표현 방식 포함

### 학습 설정
1. **Epoch**: 기본값(3-4) 사용 권장
2. **Validation**: 20% 분리하여 과적합 방지
3. **모니터링**: 학습 중 loss 추이 확인

### 비용 최적화
1. **단계적 접근**: 100개로 시작 → 효과 확인 → 500개로 확장
2. **재사용**: Fine-tuned 모델은 영구 보존, 재학습 불필요
3. **프롬프트 단순화**: Fine-tuned 모델은 짧은 프롬프트 사용 가능

---

## 예상 결과

### Baseline vs Fine-tuned

| Stage | Method | Accuracy | Cost/1k reviews |
|-------|--------|----------|-----------------|
| Baseline | Zero-shot | 78% | $15 |
| Improved | Few-shot + CoT | 88% | $28 |
| Fine-tuned | Custom Model | 95% | $12 |

### 핵심 이점
- ✅ **정확도**: 78% → 95% (+17%)
- ✅ **비용**: $28 → $12 (-57%)
- ✅ **속도**: 프롬프트 단순화로 2배 빠름
- ✅ **유지보수**: 프롬프트 관리 부담 감소

---

## 다음 단계

1. **모니터링**: 실제 사용 중 성능 추적
2. **업데이트**: 새로운 데이터로 주기적 재학습
3. **확장**: 다른 도메인/언어로 확장

---

## 참고 자료

- [OpenAI Fine-tuning Guide](https://platform.openai.com/docs/guides/fine-tuning)
- [Fine-tuning API Reference](https://platform.openai.com/docs/api-reference/fine-tuning)
- [Best Practices for Fine-tuning](https://platform.openai.com/docs/guides/fine-tuning/preparing-your-dataset)
