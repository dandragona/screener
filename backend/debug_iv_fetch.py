import sys
import os

# Fix path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from screener import Screener
from data_provider import HybridProvider, PolygonProvider
import config
import data_provider
import json

def debug_fetch():
    print(f"DEBUG: ENABLE_IV_RANK = {config.ENABLE_IV_RANK}")
    
    # Enable debug prints in PolygonProvider by monkeypatching (hacky but quick)
    # Actually I removed them. I'll rely on script output.
    
    print("Initializing...")
    hp = HybridProvider()
    s = Screener(hp)
    
    ticker = "AAPL" 
    print(f"Fetching full history for {ticker}...")
    
    # Measure time?
    import time
    start = time.time()
    
    # Force full mode
    data = s.process_ticker(ticker, fetch_mode="full")
    end = time.time()
    print(f"Fetch took {end - start:.2f} seconds")
    
    if not data:
        print("No data returned!")
        return

    iv_hist = data.get("iv_history")
    if iv_hist:
        print(f"Success! Got {len(iv_hist)} history points.")
        print("Sample:", iv_hist[0])
    else:
        print("FAILURE: No iv_history returned.")

if __name__ == "__main__":
    debug_fetch()
