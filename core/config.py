import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATA_PATH = "data"

# Analysis parameters
NEGATIVE_RATING_THRESHOLD = 3
RECENT_PERIOD_DAYS = 30
COMPARISON_PERIOD_DAYS = 60

# LLM settings
LLM_MODEL = "gpt-4o-mini"
LLM_TEMPERATURE = 0.3

# ── 리뷰 답변 생성 (외식업 배달앱) ──────────────────────────
STORE_NAME = os.getenv("STORE_NAME", "도야짬뽕 부천시청점")
# 답변 생성은 분석과 달리 한국어 문장력이 결과를 좌우한다. 실측 비교에서
# gpt-4o-mini 는 "~하셨다니 기쁩니다 … 노력하겠습니다" 정형구로 수렴했고,
# gpt-4.1-mini 는 메뉴별로 다른 문장을 냈다.
REPLY_LLM_MODEL = os.getenv("REPLY_LLM_MODEL", "gpt-4.1-mini")
# 긍정 답변은 매번 달라야 하므로 온도를 높이고, 부정 답변은 안정적으로 간다.
REPLY_POSITIVE_TEMPERATURE = float(os.getenv("REPLY_POSITIVE_TEMPERATURE", "1.0"))
REPLY_NEGATIVE_TEMPERATURE = float(os.getenv("REPLY_NEGATIVE_TEMPERATURE", "0.6"))
# 긍정 답변 길이 (공백 포함)
POSITIVE_REPLY_MIN_CHARS = 100
POSITIVE_REPLY_MAX_CHARS = 200
# 이모지를 매번 허용하면 모델이 같은 이모지(🙂)로 수렴한다. 코드에서 쓸지 말지를
# 정하고, 쓸 때도 어떤 이모지를 쓸지 지정한다.
POSITIVE_EMOJI_RATE = float(os.getenv("POSITIVE_EMOJI_RATE", "0.3"))
POSITIVE_EMOJI_POOL = ["🙂", "😊", "🍜", "🥟", "👍", "🔥"]
# 이 별점 이상이면 긍정 경로
POSITIVE_RATING_THRESHOLD = 4
# 공개 URL 남용 방지용 접속 코드. 비워 두면 잠그지 않는다.
ACCESS_CODE = os.getenv("ACCESS_CODE", "")
