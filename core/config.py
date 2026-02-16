import os

from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
DATA_PATH = "data"

# Analysis parameters
NEGATIVE_RATING_THRESHOLD = 3
RECENT_PERIOD_DAYS = 30
COMPARISON_PERIOD_DAYS = 60

# LLM settings
LLM_MODEL = "gemini-2.0-flash"
LLM_TEMPERATURE = 0.3
