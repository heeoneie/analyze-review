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
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")

# LLM settings
LLM_MODEL = "gpt-4o-mini"               # OpenAI primary model
FALLBACK_LLM_MODEL = "gemini-2.0-flash" # Google Gemini model
LLM_TEMPERATURE = 0.3
