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
