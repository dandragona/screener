from backend.screener import Screener
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from backend.data_provider import HybridProvider, PolygonProvider
import json

def debug_fetch():
    print("Initializing...")
    hp = HybridProvider()
    s = Screener(hp)
    
    ticker = "AAPL" # Use a liquid ticker
    print(f"Fetching full history for {ticker}...")
    
    # Force full mode
    data = s.process_ticker(ticker, fetch_mode="full")
    
    if not data:
        print("No data returned!")
        return

    iv_hist = data.get("iv_history")
    if iv_hist:
        print(f"Success! Got {len(iv_hist)} history points.")
        print("Sample:", iv_hist[0])
    else:
        print("FAILURE: No iv_history returned.")
        print("Keys present:", data.keys())
        if "iv30_current" in data:
            print("iv30_current:", data["iv30_current"])

if __name__ == "__main__":
    debug_fetch()
