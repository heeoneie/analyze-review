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
