from data_provider import HybridProvider, PolygonProvider, YFinanceProvider
import pandas as pd
import logging
import yfinance as yf
from datetime import datetime, timedelta

# Configure logging to see Polygon/Provider internal prints
logging.basicConfig(level=logging.INFO)

def debug_iv30():
    print("--- Starting IV30 Debug on TSLA ---")
    
    # We want to see the raw stats (Min/Max) to compare with Market Chameleon
    # So we will replicate the logic inside HybridProvider but print more info
    
    symbol = "TSLA"
    poly = PolygonProvider()
    
    # Fetch History first (needed for calc)
    print("Fetching Stock History...")
    yf_ticker = yf.Ticker(symbol)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    hist = yf_ticker.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
    
    print(f"Calculating IV Year History ({len(hist)} days)...")
    # We need to monkey-patch or inspect the internal calc to see daily values
    # Or just print the series and look for April dates
    # Since _calculate_historic_iv30 returns a list of values (floats), we lose the dates.
    # Let's temporarily modify data_provider to return dates OR mimic the logic here.
    
    # Actually, let's just inspect the return value closer or modify the provider to debug print.
    # But since we can't easily see dates from a list of floats, let's assume the series is chronological.
    # Hist starts 1 year ago.
    
    start_date_dt = pd.to_datetime(start_date.strftime('%Y-%m-%d')).tz_localize(None)
    
    iv_series = poly._calculate_historic_iv30(symbol, hist)
    
    if iv_series:
        # Re-attach approximate dates
        # Note: iv_series might be shorter than hist if some days failed
        print("IV Series Length:", len(iv_series))
        
        # Let's print out values that look high
        print("\n--- Top 10 IV Days ---")
        sorted_iv = sorted(iv_series, reverse=True)[:10]
        for val in sorted_iv:
            print(f"{val:.4f}")

        # Try to find the "April 2025" window roughly
        # If today is Jan 2026, April 2025 is ~9 months ago.
        # Index ~60 to ~90?
        
    if iv_series:
        iv_min = min(iv_series)
        iv_max = max(iv_series)
        current = iv_series[-1]
        
        print("\n--- IV Stats (1 Year) ---")
        print(f"Low:  {iv_min:.4f} ({iv_min*100:.2f}%)")
        print(f"High: {iv_max:.4f} ({iv_max*100:.2f}%)")
        print(f"Curr: {current:.4f} ({current*100:.2f}%)")
        
        if iv_max > iv_min:
            rank = (current - iv_min) / (iv_max - iv_min)
            print(f"Rank: {rank:.4f} ({rank*100:.2f}%)")
    else:
        print("FAILED: No IV Series generated")

if __name__ == "__main__":
    debug_iv30()
