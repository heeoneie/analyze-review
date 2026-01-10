# 사용 가이드

## iPhone SE 리뷰 분석 결과

업로드된 `APPLE_iPhone_SE.csv` 파일을 분석한 결과입니다.

### 데이터 개요
- 총 리뷰 수: 9,713개
- 부정 리뷰 수 (평점 3점 이하): 1,208개
- 분석 대상: 최근 30일 vs 이전 30일 비교

### 분석 결과

#### 1. TOP 3 문제점 (부정 리뷰 기준)

**1위: Battery Issue (49.0%)**
- 배터리가 빨리 소모됨
- 심각한 배터리 소모와 발열
- 발열 문제

**2위: Poor Quality (15.0%)**
- 명확하지 않은 피드백
- 가격 대비 가치 부족
- 전반적인 불만족

**3위: Positive Feedback (8.5%)**
- 전반적인 만족
- (참고: 부정 리뷰임에도 긍정적 피드백이 있는 경우)

#### 2. 최근 급증 이슈

**1위: Battery Issue (+inf%)**
- 이전: 0회 → 최근: 98회
- 배터리 문제가 급격히 증가

**2위: Display Issue (+inf%)**
- 이전: 0회 → 최근: 7회
- 디스플레이 관련 문제 발생

**3위: Camera Issue (+inf%)**
- 이전: 0회 → 최근: 5회
- 카메라 문제 증가

#### 3. AI 개선 액션 제안

1. **배터리 문제 해결**: 배터리 성능 저하 원인 파악을 위한 전수 검사 및 소프트웨어 업데이트 배포, 문제 발생한 제품에 대한 무상 교체 서비스 제공

2. **품질 관리 강화**: 제품 품질 관리를 위해 출고 전 품질 검사를 강화하고, 고객 피드백을 반영한 품질 개선 계획 수립

3. **디스플레이/카메라 개선**: 해당 제품의 특정 품질 문제를 해결하기 위해 제조 공정을 점검하고, 고객 불만을 해소할 수 있는 신속한 대응 채널 마련

---

## 커스텀 CSV로 분석 실행하기

### 1. CSV 파일 형식

CSV 파일은 다음 컬럼을 포함해야 합니다:
- `Ratings`: 평점 (1-5)
- `Reviews`: 리뷰 텍스트

예시:
```csv
Ratings,Comment,Reviews
5,Great!,This is an amazing product...
3,Okay,Battery life could be better...
1,Bad,Very disappointed with the quality...
```

### 2. 실행 명령어

```bash
python analyze_csv.py <CSV_FILE_PATH>
```

예시:
```bash
python analyze_csv.py APPLE_iPhone_SE.csv
```

### 3. 출력 예시

```
================================================================================
  Step 6: Identifying Top 3 Issues
================================================================================

[TOP 3 문제점 (부정 리뷰 기준)]

1. Battery Issue
   빈도: 98회 (49.0%)
   예시:
   - Battery drains quickly
   - Severe battery drain and heating
   - Heating problem

...
```

### 4. 주의사항

**Windows 콘솔 인코딩 문제**
- Windows 명령 프롬프트에서 한글이 깨져 보일 수 있습니다
- 이는 Windows의 기본 인코딩(CP949) 때문입니다
- 영어 출력은 정상적으로 표시됩니다

**해결 방법:**
1. PowerShell 사용 (권장)
2. 결과를 파일로 저장:
   ```bash
   python analyze_csv.py APPLE_iPhone_SE.csv > result.txt
   ```
3. UTF-8 지원 에디터로 result.txt 열기

---

## 분석 파라미터 조정

[config.py](config.py)에서 다음 설정을 변경할 수 있습니다:

```python
# 부정 리뷰 기준 (이 점수 이하를 부정 리뷰로 간주)
NEGATIVE_RATING_THRESHOLD = 3  # 1-5

# 최근 기간 (일)
RECENT_PERIOD_DAYS = 30

# 비교 기간 (일)
COMPARISON_PERIOD_DAYS = 60

# LLM 모델
LLM_MODEL = "gpt-4o-mini"  # 또는 "gpt-4"
```

---

## 비용 예상

- OpenAI API 사용료 발생
- 샘플 200개 기준: 약 $0.10-0.30
- 전체 데이터 분석 시: analyzer.py의 `sample_size` 파라미터 조정

---

## 문제 해결

### OpenAI API 키 오류
```
Error: OPENAI_API_KEY not found in .env file
```

해결: `.env` 파일 생성 후 API 키 추가
```
OPENAI_API_KEY=sk-proj-your-key-here
```

### 패키지 설치 오류
```bash
pip install -r requirements.txt
```

### CSV 형식 오류
```
ValueError: CSV must have 'Ratings' and 'Reviews' columns
```

해결: CSV 파일에 `Ratings`, `Reviews` 컬럼이 있는지 확인

---

## 다음 단계

1. 분석 결과를 팀과 공유
2. TOP 문제점에 대한 우선순위 논의
3. 급증 이슈에 대한 긴급 대응 계획 수립
4. AI 제안 액션을 실행 로드맵에 반영
5. 정기적인 리뷰 분석으로 트렌드 모니터링
