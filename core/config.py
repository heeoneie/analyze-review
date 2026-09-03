import logging
import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
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
# 실제 매장 이름은 .env 에만 둔다. 공개 레포에 고객사 이름을 기본값으로 박지 않는다.
STORE_NAME = os.getenv("STORE_NAME", "우리 매장")
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

if not ACCESS_CODE:
    # 로컬 개발에서는 정상이지만, 공개 URL 에 이 상태로 올라가면 링크를 아는
    # 누구나 OpenAI 요금을 쓴다. 조용히 지나가면 알아채지 못한다.
    logging.getLogger(__name__).warning(
        "ACCESS_CODE 가 비어 있습니다. 답글 생성 API 가 인증 없이 열립니다. "
        "공개 주소로 배포한다면 반드시 설정하세요."
    )

# ── 계정 (카카오 로그인) ────────────────────────────────────
# developers.kakao.com 에서 앱을 만들고 받은 값. 없으면 로그인 라우터가
# 503 을 내고, 기존 ACCESS_CODE 경로는 그대로 동작한다. 이렇게 해 두면
# 카카오 앱 심사를 기다리는 동안에도 서비스가 멈추지 않는다.
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")
KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI", "")

# 세션 쿠키 서명 키. 바뀌면 로그인된 사람이 전부 로그아웃된다.
SESSION_SECRET = os.getenv("SESSION_SECRET", "")

# 세션 유지 기간. 사장님이 하루에 몇 번 여는 패턴이라 짧으면 불편하다.
SESSION_MAX_AGE_DAYS = int(os.getenv("SESSION_MAX_AGE_DAYS", "30"))

KAKAO_LOGIN_ENABLED = bool(KAKAO_REST_API_KEY and KAKAO_REDIRECT_URI and SESSION_SECRET)

if KAKAO_REST_API_KEY and not SESSION_SECRET:
    # 키만 있고 서명 비밀이 없으면 세션을 못 만든다. 조용히 로그인만 안 되는
    # 상태가 되므로 시작할 때 알린다.
    logging.getLogger(__name__).warning(
        "KAKAO_REST_API_KEY 는 있는데 SESSION_SECRET 이 없어 로그인을 켤 수 없습니다. "
        "python -c \"import secrets;print(secrets.token_urlsafe(32))\" 로 만들어 넣으세요."
    )
