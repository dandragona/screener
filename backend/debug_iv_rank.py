from data_provider import HybridProvider
import pandas as pd
from datetime import datetime, timedelta

def debug_iv():
    print("--- Starting IV Rank Debug ---")
    hp = HybridProvider()
    symbol = "TSLA"
    
    # 1. Inspect Stock Data
    print(f"\n1. Fetching Stock Details for {symbol}...")
    stock_details = hp.get_ticker_details(symbol)
    curr_price = stock_details.get("current_price")
    print(f"Current Price (YF): {curr_price}")
    
    if not curr_price:
        print("ERROR: No current price.")
        return

    # 2. Inspect Contract Selection
    print("\n2. Finding ATM LEAP...")
    params = {
        "underlying_ticker": symbol,
        "expiration_date.gte": (datetime.now() + timedelta(days=300)).strftime("%Y-%m-%d"),
        "strike_price.gte": curr_price * 0.8,
        "strike_price.lte": curr_price * 1.2,
        "limit": 10,
        "sort": "expiration_date",
        "order": "asc"
    }
    # Use Poly's _get_json helper directly
    res = hp.poly._get_json("/v3/reference/options/contracts", params)
    contracts = res.get("results", [])
    print(f"Found {len(contracts)} candidate contracts.")
    if not contracts:
        print("ERROR: No contracts found.")
        return

    best_contract = min(contracts, key=lambda x: abs(x.get("strike_price") - curr_price))
    option_ticker = best_contract.get("ticker")
    print(f"Selected Contract: {option_ticker}")
    print(f"Strike: {best_contract.get('strike_price')}")
    print(f"Expiration: {best_contract.get('expiration_date')}")

    # 3. Inspect History Fetching
    print("\n3. Fetching History (1 Year)...")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    # YF
    print("Fetching YF History...")
    yf_ticker = hp.yf.get_ticker_details(symbol) # Not the raw ticker
    import yfinance as yf
    raw_yf = yf.Ticker(symbol)
    hist = raw_yf.history(start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))
    print(f"YF Stock Bars: {len(hist)}")
    if not hist.empty:
        print(f"Sample YF Date: {hist.index[0]}")
    
    # Polygon
    print("Fetching Polygon Option History...")
    opt_aggs = hp.poly._get_json(
            f"/v2/aggs/ticker/{option_ticker}/range/1/day/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}",
            {"limit": 500}
    )
    opt_results = opt_aggs.get("results", [])
    print(f"Polygon Option Bars: {len(opt_results)}")
    
    if not opt_results:
        print("ERROR: No Option Bars from Polygon. Contract might be too new or illiquid.")
        return

    # 4. Inspect Matching Logic
    print("\n4. Tracing Date Matching...")
    matches = 0
    failures = 0
    debug_limit = 5
    
    for bar in opt_results[:20]: # Check first 20
        ts = bar['t']
        dt_obj = datetime.fromtimestamp(ts / 1000.0)
        dt_str = dt_obj.strftime("%Y-%m-%d")
        
        # Check YF
        try:
            row = hist.loc[dt_str]
            matches += 1
            if matches <= debug_limit:
                print(f"MATCH: {dt_str} | Opt: {bar['c']} | Stock: {row['Close']}")
        except KeyError:
            failures += 1
            if failures <= debug_limit:
                print(f"MISS: {dt_str} not in YF index.")
                # Print YF index format comparison
                # print(f"YF Index Sample: {hist.index[0]}")
    
    print(f"\nTotal Matches: {matches}")
    print(f"Total Misses: {failures}")
    
    if matches < 10:
        print("WARNING: Very few matches. Check mismatch or data sparseness.")

if __name__ == "__main__":
    debug_iv()
