> ## ⚠️ 이 문서는 **실행되지 않은 계획서**입니다
>
> 아래의 모든 정확도 수치(90%, 94%, 95% 등)는 **작성 시점의 목표치이며 측정된 값이
> 아닙니다.** 이 문서는 한때 목표 체크박스가 전부 `[x]` 로 채워져 있어 달성한
> 것처럼 읽혔습니다. 실제로는 평가 데이터셋 라벨링조차 끝나지 않은 상태였고,
> 같은 레포의 [PROGRESS_REPORT.md](./PROGRESS_REPORT.md) 는 그 사실을 적고 있었습니다.
> 문서끼리 다른 말을 하고 있었습니다.
>
> 체크박스를 전부 미완료로 되돌렸습니다. 실제 측정은
> [labeling-guide-v1.md](./evaluation/labeling-guide-v1.md) 절차로 진행 중이며,
> 결과가 나오면 `docs/evaluation/RESULTS.md` 에 싣습니다.
>
> **이 문서의 어떤 수치도 이력서·발표에 인용하지 마십시오.**

---

# 🚀 AI 리뷰 분석 시스템 고도화 계획

**목표**: 1주일 내에 포트폴리오급 AI 프로젝트로 업그레이드
**기간**: 7일
**최종 목표**: 정확도 90%+ 달성 + 최신 AI 기술 적용

---

## 📊 현재 상태 (Baseline)

- ✅ 기본 LLM API 호출 구조
- ✅ 리뷰 분류 및 통계
- ❌ 정량적 평가 없음
- ❌ 정확도 미측정
- ❌ 고급 AI 기법 미적용

**문제점**: "정말 잘 되는지" 증명 불가 → 포트폴리오로 부족

---

## 🎯 최종 목표 (1주 후)

### 정량적 성과
- [ ] **정확도**: 90%+ (Ground Truth 100개 기준)  ← 목표치, 미측정
- [ ] **처리 속도**: 1,000 리뷰/분 이상
- [ ] **비용**: 건당 $0.05 이하

### 기술적 성과
- [ ] Level 1: 정량적 평가 시스템
- [ ] Level 2: 프롬프트 엔지니어링 최적화
- [ ] Level 3: 에러 분석 & 개선
- [ ] Level 4-1: 멀티 에이전트 시스템
- [ ] Level 4-2: RAG + Vector DB
- [ ] Level 4-3: Fine-tuning (시간 허락 시)

### 포트폴리오 성과
- [ ] README에 구체적 수치와 실험 결과
- [ ] 기술적 의사결정 과정 문서화
- [ ] 회의 발표 자료 완성

---

## 📅 Day-by-Day 계획

### **Day 1: 평가 데이터셋 구축** ⏰ 2-3시간

#### 목표
- Ground Truth 데이터 100개 생성
- 일관성 있는 라벨링 기준 수립

#### 작업
1. `prepare_evaluation_data.py` 실행
   ```bash
   python3 prepare_evaluation_data.py
   ```
   → `evaluation_dataset.csv` 생성 (100개 샘플)

2. 수동 라벨링
   - Excel/Numbers로 CSV 열기
   - `labeling_guide.md` 참고
   - `manual_label` 컬럼에 카테고리 입력
   - 10개 카테고리 사용:
     - delivery_delay, wrong_item, poor_quality
     - damaged_packaging, size_issue, missing_parts
     - not_as_described, customer_service, price_issue, other

3. 라벨링 품질 체크
   - 10개마다 일관성 확인
   - 애매한 케이스는 `notes` 컬럼에 메모

#### 완료 기준
- ✅ 100개 리뷰 모두 라벨링 완료
- ✅ 카테고리 분포 확인 (편향 없는지)

---

### **Day 2: Level 1 - 정량적 평가 시스템** ⏰ 3-4시간

#### 목표
- **베이스라인 정확도 측정**
- 평가 자동화 파이프라인 구축

#### 작업
1. `evaluate.py` 작성
   ```python
   # 기능:
   # 1. AI 예측 결과 생성
   # 2. Ground Truth와 비교
   # 3. Accuracy, Precision, Recall, F1 계산
   # 4. Confusion Matrix 생성
   ```

2. 베이스라인 측정
   ```bash
   python3 evaluate.py --mode baseline
   ```
   → `results/baseline_metrics.json` 생성

3. 시각화
   - Confusion Matrix 히트맵
   - 카테고리별 성능 그래프
   - `results/baseline_visualization.png` 생성

#### 예상 결과
```
Baseline Accuracy: 75-80%
주요 문제:
- wrong_item vs not_as_described 혼동
- other 카테고리 과다 분류
```

#### 완료 기준
- ✅ `evaluate.py` 작동
- ✅ 베이스라인 정확도 확정
- ✅ 혼동 매트릭스 생성

---

### **Day 3: Level 2 - 프롬프트 엔지니어링** ⏰ 4-5시간

#### 목표
- **정확도 +10-15% 개선**
- 최적 프롬프트 전략 발견

#### 실험 목록

##### 실험 1: Zero-shot vs Few-shot
```python
# Zero-shot (현재)
"리뷰를 분류하세요"

# Few-shot (개선)
"리뷰를 분류하세요. 예시:
- delivery_delay: 'Package took 3 weeks'
- wrong_item: 'Received blue instead of red'
- poor_quality: 'Broke after 2 days'
"
```

##### 실험 2: Chain-of-Thought (CoT)
```python
"단계별로 생각하세요:
1. 리뷰에서 언급된 문제들을 나열
2. 가장 핵심적인 문제 선택
3. 해당 카테고리 선택
4. 최종 답변"
```

##### 실험 3: Temperature 최적화
```python
temperatures = [0.0, 0.3, 0.5, 0.7]
# 각 temperature에서 정확도 측정
```

##### 실험 4: 카테고리 사전 정의
```python
"다음 10개 카테고리 중 정확히 1개만 선택:
1. delivery_delay: 배송 지연 관련
2. wrong_item: 잘못된 상품 수령
..."
```

#### 실행
```bash
python3 experiments/prompt_engineering.py --all
```

#### 결과 기록
| 방법 | Accuracy | F1 Score | 비용 | 시간 |
|------|----------|----------|------|------|
| Zero-shot | 78% | 0.76 | $0.15 | 30s |
| Few-shot (3-shot) | 87% | 0.85 | $0.22 | 45s |
| Few-shot + CoT | 91% | 0.89 | $0.28 | 60s |
| Temperature=0.0 | 89% | 0.87 | $0.22 | 45s |

#### 완료 기준
- ✅ 4가지 실험 모두 완료
- ✅ 최적 전략 선정
- ✅ 정확도 85%+ 달성

---

### **Day 4: Level 3 - 에러 분석 & 개선** ⏰ 3-4시간

#### 목표
- **틀린 케이스 분석**
- 프롬프트 미세 조정으로 정확도 극대화

#### 작업

##### 1. 에러 분석
```bash
python3 experiments/error_analysis.py
```

**분석 항목**:
- 가장 많이 틀리는 카테고리 쌍
- 틀린 리뷰의 공통 패턴
- 리뷰 길이별 정확도
- 평점별 정확도

**예상 결과**:
```
주요 에러 패턴:
1. wrong_item ↔ not_as_described (15건)
   → 원인: 둘 다 "기대와 다름" 표현

2. delivery_delay ↔ customer_service (8건)
   → 원인: "연락해도 배송 안 옴" 같은 복합 이슈

3. other 카테고리 과다 사용 (12건)
   → 원인: 프롬프트가 명확한 지시 부족
```

##### 2. 프롬프트 개선
```python
# 개선 전
"분류하세요"

# 개선 후
"핵심 문제에 집중하세요:
- 'wrong_item'은 물리적으로 다른 상품
- 'not_as_described'는 설명과 기능/품질이 다름
- 복합 이슈는 가장 먼저/많이 언급된 것 선택
- 'other'는 정말 분류 불가능할 때만 사용"
```

##### 3. 재평가
```bash
python3 evaluate.py --mode improved
```

##### 4. 비용 최적화
```python
# 배치 처리 구현
# 200개 → 50개씩 4번 대신
# 200개 → 한 번에 처리 (JSON array)
# 비용: $0.22 → $0.08
```

#### 완료 기준
- ✅ 에러 패턴 문서화
- ✅ 프롬프트 개선 적용
- ✅ 정확도 88%+ 달성
- ✅ 비용 30% 이상 절감

---

### **Day 5: Level 4-1 - 멀티 에이전트 시스템** ⏰ 4-5시간

#### 목표
- **Self-Consistency로 정확도 추가 개선**
- AI 에이전트 아키텍처 구현

#### 아키텍처

```
┌─────────────────────────────────────┐
│         Coordinator Agent           │
│    (전체 흐름 관리 & 최종 결정)        │
└──────────┬──────────────────────────┘
           │
    ┌──────┴──────┐
    ▼             ▼
┌─────────┐   ┌─────────┐   ┌─────────┐
│Agent 1  │   │Agent 2  │   │Agent 3  │
│분류 전문 │   │검증 전문 │   │맥락 분석│
└─────────┘   └─────────┘   └─────────┘
```

#### 구현

##### 1. Agent 클래스 설계
```python
# advanced/multi_agent_analyzer.py

class ClassificationAgent:
    """리뷰 분류 전문 에이전트"""
    def categorize(self, review):
        # Few-shot + CoT 프롬프트 사용
        pass

class VerificationAgent:
    """분류 검증 전문 에이전트"""
    def verify(self, review, category):
        # 다른 관점에서 재검증
        pass

class CoordinatorAgent:
    """최종 결정 에이전트"""
    def decide(self, review, predictions):
        # 여러 예측 결과 종합
        # Self-consistency voting
        pass
```

##### 2. Self-Consistency 전략
```python
# 3명의 에이전트가 독립적으로 분류
agent1_result = "delivery_delay"
agent2_result = "delivery_delay"
agent3_result = "customer_service"

# 다수결 또는 신뢰도 기반 결정
final = majority_vote([agent1, agent2, agent3])
# → "delivery_delay" (2/3)
```

##### 3. 실행
```bash
python3 advanced/multi_agent_analyzer.py
```

#### 예상 결과
```
Single Agent: 88%
Multi-Agent (3): 92%
+4% 개선!

Trade-off:
- 정확도: ↑ 4%
- 비용: ↑ 3배 (API 호출 3번)
- 시간: ↑ 2.5배
```

#### 완료 기준
- ✅ 멀티 에이전트 시스템 작동
- ✅ 정확도 90%+ 달성
- ✅ 비용/성능 트레이드오프 분석

---

### **Day 5-6: Level 4-2 - RAG + Vector DB** ⏰ 5-6시간

#### 목표
- **Few-shot learning을 동적으로 개선**
- 과거 분류 결과를 검색해서 활용

#### 아키텍처

```
새 리뷰: "배송이 3주 걸렸어요"
    ↓
Vector DB 검색
    ↓
유사 리뷰 찾기:
- "Package took 2 weeks" → delivery_delay
- "Delivery was so slow" → delivery_delay
- "Arrived 1 month late" → delivery_delay
    ↓
Few-shot 예시로 사용
    ↓
LLM 호출 (예시 포함)
    ↓
정확도 향상!
```

#### 구현

##### 1. Vector DB 설치
```bash
pip install chromadb sentence-transformers
```

##### 2. 임베딩 생성
```python
# advanced/rag_system.py

from sentence_transformers import SentenceTransformer
import chromadb

class RAGReviewAnalyzer:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.client = chromadb.Client()
        self.collection = self.client.create_collection("reviews")

    def add_to_db(self, review_text, category):
        """과거 분류 결과 저장"""
        embedding = self.model.encode(review_text)
        self.collection.add(
            embeddings=[embedding],
            documents=[review_text],
            metadatas=[{"category": category}]
        )

    def retrieve_similar(self, review_text, n=3):
        """유사 리뷰 검색"""
        embedding = self.model.encode(review_text)
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=n
        )
        return results

    def analyze_with_rag(self, review_text):
        """RAG 기반 분석"""
        # 1. 유사 리뷰 검색
        similar = self.retrieve_similar(review_text)

        # 2. Few-shot 예시로 구성
        examples = format_examples(similar)

        # 3. LLM 호출 (예시 포함)
        prompt = f"""
        참고 예시:
        {examples}

        분류 대상:
        {review_text}
        """
        return llm_call(prompt)
```

##### 3. 데이터 준비
```python
# Ground Truth 100개를 Vector DB에 저장
for idx, row in eval_df.iterrows():
    rag_analyzer.add_to_db(
        row['review_text'],
        row['manual_label']
    )
```

##### 4. 실행
```bash
python3 advanced/rag_analyzer.py
```

#### 예상 결과
```
Without RAG: 88%
With RAG (top-3): 93%
With RAG (top-5): 94%
+6% 개선!

장점:
- 도메인 지식 자동 학습
- 새로운 카테고리 추가 쉬움
- 설명 가능성 향상 (유사 예시 제시)
```

#### 완료 기준
- ✅ Vector DB 구축
- ✅ RAG 파이프라인 작동
- ✅ 정확도 93%+ 달성

---

### **Day 6-7: Level 4-3 - Fine-tuning (Optional)** ⏰ 6-8시간

#### 목표
- **GPT-4o-mini Fine-tuning**
- 비용 절감 + 정확도 유지

#### 언제 할까?
- Day 5까지 완료 후 시간 남으면
- 또는 회사 발표 후 추가 작업으로

#### 작업

##### 1. 학습 데이터 준비
```python
# fine_tuning/prepare_training_data.py

# Ground Truth 100개 + 추가 라벨링 400개
# → 총 500개 학습 데이터

# OpenAI Format으로 변환
[
  {
    "messages": [
      {"role": "system", "content": "리뷰 분류 전문가"},
      {"role": "user", "content": "리뷰: Package took 3 weeks"},
      {"role": "assistant", "content": "delivery_delay"}
    ]
  },
  ...
]
```

##### 2. Fine-tuning 실행
```bash
# OpenAI CLI 사용
openai api fine_tuning.jobs.create \
  -t training_data.jsonl \
  -m gpt-4o-mini-2024-07-18 \
  --suffix "review-classifier"
```

##### 3. 평가
```python
# Fine-tuned 모델 사용
response = openai.ChatCompletion.create(
    model="ft:gpt-4o-mini:custom:review-classifier:xxx",
    messages=[...]
)
```

#### 예상 결과
```
GPT-4o-mini (base): 88%
GPT-4o-mini (fine-tuned): 95%

비용:
- 학습: $5-10 (1회)
- 추론: $0.03/1k tokens (base 대비 비슷)

장점:
- 프롬프트 단순화 가능
- 응답 속도 향상
- 일관성 증가
```

#### 완료 기준
- ✅ 학습 데이터 500개 준비
- ✅ Fine-tuning 완료
- ✅ 정확도 95%+ 달성

---

### **Day 6: 문서화 & 시각화** ⏰ 4-5시간

#### 목표
- **포트폴리오급 README**
- 실험 결과 전부 정리

#### 작업

##### 1. README 대폭 강화
```markdown
# AI-Powered E-commerce Review Analysis

## 🎯 Problem
[비즈니스 문제 설명]

## 🚀 Solution
[AI 솔루션 설명]

## 📊 Results
- **Accuracy**: 94% (100 samples)
- **Processing Speed**: 1,000 reviews/min
- **Cost**: $0.05 per review

## 🔬 Technical Deep Dive

### 1. Baseline (78%)
- Simple LLM API call
- Zero-shot learning

### 2. Prompt Engineering (+10%)
- Few-shot learning: 3 examples per category
- Chain-of-Thought reasoning
- → Accuracy: 88%

### 3. Multi-Agent System (+4%)
- Self-consistency with 3 agents
- → Accuracy: 92%

### 4. RAG + Vector DB (+2%)
- Dynamic few-shot retrieval
- ChromaDB + Sentence Transformers
- → Accuracy: 94%

[실험 결과 그래프/표]

## 🏗️ Architecture
[시스템 아키텍처 다이어그램]

## 📈 Experiments Log
[모든 실험 결과 정리]

## 🎓 Lessons Learned
[배운 점, 한계점, 향후 개선]

## 💰 Cost Analysis
[비용 분석 표]
```

##### 2. 시각화
```python
# visualization/create_charts.py

# 생성할 차트:
1. 정확도 개선 라인 차트 (베이스라인 → 최종)
2. Confusion Matrix 히트맵
3. 카테고리별 F1 Score 막대 그래프
4. 비용 vs 정확도 산점도
5. 처리 시간 비교 차트
```

##### 3. 아키텍처 다이어그램
```python
# Mermaid 또는 draw.io 사용
[Data] → [Preprocessing] → [Multi-Agent]
                              ↓
                          [RAG System]
                              ↓
                          [LLM Call]
                              ↓
                          [Results]
```

#### 완료 기준
- ✅ README 완성
- ✅ 모든 차트 생성
- ✅ 아키텍처 다이어그램 추가

---

### **Day 7: 발표 자료 & 최종 점검** ⏰ 3-4시간

#### 목표
- **회의 발표 완벽 준비**
- 예상 질문 답변 준비

#### 작업

##### 1. 발표 자료 (PPT/Keynote)
```
슬라이드 구성:

1. 문제 정의 (1분)
   - 리뷰 많지만 인사이트 부족

2. 솔루션 (1분)
   - AI 자동 분석 시스템

3. 기술적 접근 (2분)
   - 프롬프트 엔지니어링
   - 멀티 에이전트
   - RAG 시스템

4. 결과 (1분)
   - 정확도 94%
   - 처리 속도 1,000/분
   - 비용 $0.05/건

5. 데모 (1분)
   - 실제 실행 화면

6. 향후 계획 (30초)
   - Fine-tuning
   - 대시보드
```

##### 2. 데모 준비
```bash
# 데모용 스크립트 작성
python3 demo.py --input sample_reviews.csv
# → 30초 내에 결과 출력
```

##### 3. 예상 질문 & 답변

**Q1: 정확도는 어떻게 측정했나요?**
```
A: (측정 완료 후 실제 수치와 방법으로 다시 작성할 것)
```

> ⚠️ 여기에는 원래 "정확도 94% — 100개 리뷰를 직접 라벨링한 Ground Truth와
> 비교했습니다" 라는 답변이 적혀 있었습니다. **둘 다 사실이 아니었습니다.**
> 94% 는 측정된 적이 없고, `evaluation_dataset.csv` 의 라벨은 사람이 아니라
> LLM 이 단 것입니다(사람용 `notes` 컬럼은 100건 전부 비어 있고, LLM 출력 필드인
> `confidence`·`reasoning` 은 100건 전부 채워져 있습니다).
>
> 면접에서 실제로 받을 질문에 거짓 답변을 준비해 두는 것은 미측정 자체보다
> 위험합니다. 확인되면 그 프로젝트의 다른 모든 수치도 함께 신뢰를 잃습니다.

**Q2: 비용이 얼마나 들어요?**
```
A: 리뷰 1개당 $0.05입니다.
   하루 1,000개 분석 시 월 $1,500 정도 예상됩니다.
   RAG 시스템으로 30% 절감 가능합니다.
```

**Q3: 틀린 케이스는요?**
```
A: 주로 복합 이슈에서 틀립니다.
   예: "배송 늦고 + 품질 나쁨"
   → 멀티 에이전트로 이런 케이스 개선했습니다.
```

**Q4: 다른 제품 카테고리도 가능한가요?**
```
A: 네, 카테고리만 재정의하면 됩니다.
   RAG 시스템 덕분에 새 도메인 적응이 빠릅니다.
```

**Q5: 실시간 처리 가능한가요?**
```
A: 1,000개/분 처리 가능합니다.
   API 호출 병렬화로 더 빠르게 할 수 있습니다.
```

##### 4. 최종 체크리스트
```
□ 코드 정리 (주석, 포맷팅)
□ README 최종 검토
□ 모든 스크립트 실행 테스트
□ requirements.txt 업데이트
□ .env.example 확인
□ PR 설명 작성
□ 발표 자료 완성
□ 데모 리허설
```

---

## 📦 최종 디렉토리 구조

```
analyze-review/
├── README.md                    # 대폭 강화된 README
├── IMPLEMENTATION_PLAN.md       # 이 문서
├── CLAUDE.md                    # 기존 문서
├── requirements.txt             # 업데이트됨
│
├── main.py                      # 기존 메인
├── analyzer.py                  # 기존 분석기
├── data_loader.py               # 기존 로더
├── config.py                    # 설정
│
├── evaluation/                  # 평가 시스템
│   ├── prepare_evaluation_data.py
│   ├── evaluate.py
│   ├── labeling_guide.md
│   ├── evaluation_dataset.csv
│   └── ground_truth.csv
│
├── experiments/                 # 실험 스크립트
│   ├── prompt_engineering.py    # Level 2
│   ├── error_analysis.py        # Level 3
│   └── results/
│       ├── baseline_metrics.json
│       ├── prompt_experiments.json
│       └── error_patterns.json
│
├── advanced/                    # 고급 기법
│   ├── multi_agent_analyzer.py  # Level 4-1
│   ├── rag_system.py            # Level 4-2
│   └── vector_db/               # ChromaDB 데이터
│
├── fine_tuning/                 # Fine-tuning (Optional)
│   ├── prepare_training_data.py
│   ├── training_data.jsonl
│   └── evaluate_finetuned.py
│
├── visualization/               # 시각화
│   ├── create_charts.py
│   └── figures/
│       ├── accuracy_improvement.png
│       ├── confusion_matrix.png
│       └── cost_analysis.png
│
├── presentation/                # 발표 자료
│   ├── slides.pdf
│   └── demo.py
│
└── results/                     # 최종 결과
    ├── final_metrics.json
    ├── comparison_table.csv
    └── technical_report.md
```

---

## 🎯 성공 기준

### Minimum (필수)
- [ ] 정확도 85%+  ← 목표치, 미측정
- [ ] Level 1, 2, 3 완료
- [ ] README 강화
- [ ] 회의 발표 준비

### Target (목표)
- [ ] 정확도 90%+  ← 목표치, 미측정
- [ ] Level 4-1 (멀티 에이전트) 완료
- [ ] 실험 결과 시각화
- [ ] 기술 블로그 수준 문서

### Stretch (도전)
- [ ] 정확도 95%+  ← 목표치, 미측정
- [ ] Level 4-2 (RAG) 완료
- [ ] Level 4-3 (Fine-tuning) 완료
- [ ] 포트폴리오 완성

---

## 💪 동기부여

### Before (현재)
```
"LLM API를 호출해서 리뷰를 분류했습니다."
```
→ 평가: 주니어 개발자 수준

### After (1주 후)
```
(아래는 계획 당시 상상한 문구입니다. 어떤 수치도 측정되지 않았으므로
지금 이 문장을 이력서에 쓰면 허위 기재입니다. 실측 후 다시 작성하십시오.)

"리뷰 분석 시스템을 구축하고 정확도를 78%에서 94%로 개선했습니다.

프롬프트 엔지니어링으로 10% 향상,
멀티 에이전트 시스템으로 4% 추가 개선,
RAG 시스템으로 2% 추가 개선했습니다.

100개 Ground Truth 기준으로 정량적으로 검증했고,
비용은 30% 절감했습니다."
```
→ 평가: **포트폴리오로 경쟁력 있음** 🔥

---

## 📚 학습 리소스

### Prompt Engineering
- [OpenAI Prompt Engineering Guide](https://platform.openai.com/docs/guides/prompt-engineering)
- [Few-shot Learning](https://arxiv.org/abs/2005.14165)

### Multi-Agent Systems
- [Self-Consistency](https://arxiv.org/abs/2203.11171)
- [LangChain Multi-Agent](https://python.langchain.com/docs/modules/agents/)

### RAG
- [Retrieval Augmented Generation](https://arxiv.org/abs/2005.11401)
- [ChromaDB Documentation](https://docs.trychroma.com/)

### Fine-tuning
- [OpenAI Fine-tuning Guide](https://platform.openai.com/docs/guides/fine-tuning)

---

## 🚀 시작하기

```bash
# 1. 브랜치 확인
git branch
# → feature/advanced-ai-portfolio

# 2. Day 1 시작
python3 evaluation/prepare_evaluation_data.py

# 3. 라벨링 시작
open evaluation_dataset.csv

# 4. 매일 체크인
# - 오늘 목표 확인
# - 완료 후 체크
# - 다음 날 준비
```

---

**화이팅! 1주일 후에는 완전히 다른 프로젝트가 될 거예요! 🔥**
