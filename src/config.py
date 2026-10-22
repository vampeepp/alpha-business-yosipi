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

# Data file locations conforming to Hackathon Appendix 1 & 2
CLIENT_DATA_CSV = DATA_DIR / "df_Uid_data_hack.csv"
PERSONS_DATA_CSV = DATA_DIR / "df_Fid_Uid_link_hack.csv"
PAYMENTS_DATA_CSV = DATA_DIR / "df_Uid_payment_hack.csv"
ALFA_MACRO_RESEARCH_JSON = DATA_DIR / "alfa_macro_research.json"
EXTERNAL_NEWS_JSON = DATA_DIR / "external_news_stream.json"

# Server configuration
SERVER_HOST = os.getenv("HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("PORT", "8080"))

# LLM Configuration (Slide 18 approved models)
# 1. Gemma 4 26B A4B
# 2. GLM-5.3-Flash
# 3. Qwen3.6 35B A3B
# 4. DeepSeek-V4.1-Flash
# 5. Qwen3-VL-30B-A3B-Instruct
# 6. Kimi-K2.6
DEFAULT_LLM_MODEL = os.getenv("LLM_MODEL", "Qwen3.6-35B-A3B")
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")

# Scoring & Agent Parameters
MIN_RELEVANCE_THRESHOLD = float(os.getenv("MIN_RELEVANCE_THRESHOLD", "30.0"))
MAX_SUPPLY_CHAIN_DEPTH = int(os.getenv("MAX_SUPPLY_CHAIN_DEPTH", "2"))
CRITIC_PASSING_SCORE = float(os.getenv("CRITIC_PASSING_SCORE", "85.0"))
