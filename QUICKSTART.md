# 빠른 시작 가이드

## 5분 안에 실행하기

### 1. 필수 준비물
- Python 3.8 이상
- OpenAI API 키 ([여기서 발급](https://platform.openai.com/api-keys))
- Kaggle 계정 (데이터셋 다운로드용)

### 2. Kaggle API 설정 (최초 1회)

Kaggle API 인증을 위해 API 토큰이 필요합니다:

1. [Kaggle](https://www.kaggle.com/) 로그인
2. Account → API → "Create New API Token" 클릭
3. `kaggle.json` 파일 다운로드
4. 파일을 적절한 위치에 배치:
   - **Linux/Mac**: `~/.kaggle/kaggle.json`
   - **Windows**: `C:\Users\<username>\.kaggle\kaggle.json`

### 3. 설치 및 실행

```bash
# 1. 가상환경 생성 (권장)
python -m venv venv

# 가상환경 활성화
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 2. 패키지 설치
pip install -r requirements.txt

# 3. 환경변수 설정
# .env 파일 생성하고 아래 내용 추가:
# OPENAI_API_KEY=sk-your-api-key-here

# Windows에서 .env 파일 생성:
echo OPENAI_API_KEY=sk-your-api-key-here > .env

# Mac/Linux에서 .env 파일 생성:
echo "OPENAI_API_KEY=sk-your-api-key-here" > .env

# 4. 실행!
python main.py
```

### 4. 예상 실행 시간
- 첫 실행: 5-10분 (데이터 다운로드 포함)
- 이후 실행: 2-3분

### 5. 문제 해결

#### "OPENAI_API_KEY not found" 에러
```bash
# .env 파일이 제대로 생성되었는지 확인
cat .env  # Mac/Linux
type .env  # Windows

# 내용이 다음과 같아야 함:
# OPENAI_API_KEY=sk-proj-...
```

#### Kaggle API 인증 에러
```bash
# kaggle.json 위치 확인
# Windows: C:\Users\<username>\.kaggle\kaggle.json
# Mac/Linux: ~/.kaggle/kaggle.json

# 파일 권한 설정 (Mac/Linux)
chmod 600 ~/.kaggle/kaggle.json
```

#### 패키지 설치 오류
```bash
# pip 업그레이드
python -m pip install --upgrade pip

# 다시 설치
pip install -r requirements.txt
```

### 6. 출력 예시

실행하면 다음과 같은 형식으로 결과가 출력됩니다:

```
================================================================================
  E-commerce Review Analysis PoC
================================================================================

================================================================================
  Step 1: Loading Data
================================================================================
Downloading dataset from Kaggle...
Dataset downloaded to: ...
Loaded 41,455 reviews with text
Date range: 2016-10-04 to 2018-08-29

================================================================================
  Step 6: Identifying Top 3 Issues
================================================================================

📊 TOP 3 문제점 (부정 리뷰 기준):

1. Delivery Delay
   빈도: 145회 (32.1%)
   예시:
   - Package arrived 2 weeks late
   ...

💡 개선 액션 제안:

1. 배송 파트너사와 긴급 미팅을 통해 최근 지연 원인 파악...
...
```

### 7. 다음 단계

분석 결과가 나오면:
1. TOP 3 문제점을 팀과 공유
2. 급증 이슈가 있다면 우선순위로 대응
3. AI가 제안한 개선 액션을 실행 계획에 반영

---

궁금한 점이 있으면 [README.md](README.md)를 참고하세요!
