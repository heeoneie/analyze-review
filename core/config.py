import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
# YouTube Data API v3: YOUTUBE_API_KEY 없으면 GOOGLE_API_KEY로 폴백
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY") or os.getenv("GOOGLE_API_KEY")
DATA_PATH = "data"

# Analysis parameters
NEGATIVE_RATING_THRESHOLD = 3
RECENT_PERIOD_DAYS = 30
COMPARISON_PERIOD_DAYS = 60

# LLM provider: "openai" (prod default) or "google" (local dev)
_VALID_LLM_PROVIDERS = {"openai", "google"}
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").strip().lower()
if LLM_PROVIDER not in _VALID_LLM_PROVIDERS:
    raise ValueError(
        f"LLM_PROVIDER must be one of {_VALID_LLM_PROVIDERS}, got '{LLM_PROVIDER}'"
    )

# LLM settings
LLM_MODEL = "gpt-4o-mini"               # OpenAI primary model
FALLBACK_LLM_MODEL = "gemini-2.0-flash" # Google Gemini model
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
# HTTP 헤더로 실어 보내므로 ASCII 만 쓸 수 있다. 한국어를 넣으면 브라우저가
# 요청 자체를 못 만들어서, 서버는 멀쩡한데 아무도 못 들어오는 상태가 된다.
# 조용히 넘기면 원인을 찾기 어려우므로 시작할 때 바로 막는다.
ACCESS_CODE = os.getenv("ACCESS_CODE", "")

if ACCESS_CODE and not ACCESS_CODE.isascii():
    raise ValueError(
        "ACCESS_CODE 에는 ASCII 문자만 쓸 수 있습니다 (영문·숫자·기호). "
        "HTTP 헤더로 전송되기 때문입니다. 예: doya-1877"
    )
