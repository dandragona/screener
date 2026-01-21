import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))
from backend.symbol_loader import get_sp1500_tickers

def verify():
    print("Fetching S&P 1500 tickers...")
    tickers = get_sp1500_tickers()
    print(f"Fetched {len(tickers)} tickers.")
    if len(tickers) > 1400:
        print("Success: Ticker count seems reasonable for S&P 1500.")
        print(f"Sample: {tickers[:5]}")
    else:
        print("Warning: Ticker count seems low.")

if __name__ == "__main__":
    verify()
