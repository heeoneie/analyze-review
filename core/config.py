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

# LLM settings (primary: OpenAI, fallback: Gemini)
LLM_MODEL = "gpt-4o-mini"
FALLBACK_LLM_MODEL = "gemini-2.0-flash"
LLM_TEMPERATURE = 0.3
