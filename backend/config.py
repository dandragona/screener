from typing import List

# Default tickers for the screener (MVP list)
DEFAULT_TICKERS: List[str] = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "AMD", "INTC", 
    "PYPL", "NFLX", "ADBE", "CRM", "CSCO", "PEP", "KO"
]

# Screening Criteria
MIN_MARKET_CAP = 2_000_000_000  # 2 Billion
MAX_P_FCF = 20.0
MAX_PEG = 1.5
MIN_ROE = 0.15

# API Configuration
API_TITLE = "LEAPs Screener API"
API_HOST = "0.0.0.0"
API_PORT = 8000

# Polygon.io Configuration
import os
from dotenv import load_dotenv

load_dotenv()

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
if not POLYGON_API_KEY:
    raise ValueError("POLYGON_API_KEY not found in environment variables. Please set it in a .env file.")

# Feature Flags
ENABLE_IV_RANK = os.getenv("ENABLE_IV_RANK", "False").lower() == "true"
