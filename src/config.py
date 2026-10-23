"""
Configuration module for Alfa-Bank Corporate News Analytics & Insight Platform.
Maintains path constants, environment variables, default threshold parameters,
and LLM configuration conforming to Hackathon guidelines (Slide 18).
"""

import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# Automatically load local .env if present
def _load_env_file():
    env_file = BASE_DIR / ".env"
    if env_file.is_file():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("\"'")
                        if k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass

_load_env_file()

# Data file locations conforming to Hackathon Appendix 1 & 2
CLIENT_DATA_CSV = DATA_DIR / "df_Uid_data_hack.csv"
PERSONS_DATA_CSV = DATA_DIR / "df_Fid_Uid_link_hack.csv"
PAYMENTS_DATA_CSV = DATA_DIR / "df_Uid_payment_hack.csv"
ALFA_MACRO_RESEARCH_JSON = DATA_DIR / "alfa_macro_research.json"
EXTERNAL_NEWS_JSON = DATA_DIR / "external_news_stream.json"

# Server configuration
SERVER_HOST = os.getenv("HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("PORT", "8080"))

# LLM Configuration conforming to AlfaHack / Boosters instructions
# Model default: qwen/qwen3.8-27b
# Primary Base URL: https://changellenge.up.railway.app/v1
# Fallback Base URL: https://api.alfahack-gateway26.ru/v1
DEFAULT_LLM_MODEL = os.getenv("OPENAI_MODEL", os.getenv("LLM_MODEL", "qwen/qwen3.8-27b"))
LLM_API_BASE = os.getenv("OPENAI_BASE_URL", os.getenv("LLM_API_BASE", "https://changellenge.up.railway.app/v1"))
LLM_API_KEY = os.getenv("OPENAI_API_KEY", os.getenv("LLM_API_KEY", ""))



# Scoring & Agent Parameters
MIN_RELEVANCE_THRESHOLD = float(os.getenv("MIN_RELEVANCE_THRESHOLD", "30.0"))
MAX_SUPPLY_CHAIN_DEPTH = int(os.getenv("MAX_SUPPLY_CHAIN_DEPTH", "2"))
CRITIC_PASSING_SCORE = float(os.getenv("CRITIC_PASSING_SCORE", "85.0"))
