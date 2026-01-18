import os
import time
import httpx
import pandas as pd
from typing import List
from io import StringIO
from config import DEFAULT_TICKERS

SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
SP400_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies"
SP600_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies"

# Use absolute path for cache to avoid CWD issues
CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sp1500_cache.csv")
CACHE_DURATION_SECONDS = 24 * 60 * 60  # 24 hours

import subprocess
from io import StringIO

def fetch_wiki_table(url: str) -> List[str]:
    """Helper to fetch tickers from a Wikipedia URL using curl and pandas."""
    try:
        # Use curl to impersonate a browser and bypass some bot checks
        cmd = [
            'curl', '-s', '-A', 
            'Mozilla/5.0 (X11; Linux x86_64; rv:100.0) Gecko/20100101 Firefox/100.0', 
            url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        html_content = result.stdout
        
        # Parse tables
        dfs = pd.read_html(StringIO(html_content))
        
        # Usually the first table contains the constituents
        df = dfs[0]
        
        # Column names vary: 'Symbol', 'Ticker', 'Ticker symbol'
        # Standardize to 'Symbol'
        target_col = None
        for col in ['Symbol', 'Ticker', 'Ticker symbol']:
            if col in df.columns:
                target_col = col
                break
        
        if target_col:
            return df[target_col].tolist()
        return []
        
    except Exception as e:
        print(f"Error fetching from {url}: {e}")
        return []

def get_sp1500_tickers() -> List[str]:
    """
    Fetches the S&P 1500 (500 + 400 + 600) tickers from cache or Wikipedia.
    Returns a list of ticker symbols.
    """
    # Ensure data directory exists
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)

    # Check if cache exists and is fresh
    if os.path.exists(CACHE_FILE):
        file_age = time.time() - os.path.getmtime(CACHE_FILE)
        if file_age < CACHE_DURATION_SECONDS:
            try:
                df = pd.read_csv(CACHE_FILE)
                if 'Ticker' in df.columns:
                    return df['Ticker'].tolist()
            except Exception as e:
                print(f"Error reading cache: {e}")

    # Fetch from Wikipedia
    print("Fetching S&P 1500 lists from Wikipedia...")
    tickers = set()
    
    tickers.update(fetch_wiki_table(SP500_URL))
    tickers.update(fetch_wiki_table(SP400_URL))
    tickers.update(fetch_wiki_table(SP600_URL))
    
    if tickers:
        ticker_list = sorted(list(tickers))
        # Save to cache
        try:
            pd.DataFrame({'Ticker': ticker_list}).to_csv(CACHE_FILE, index=False)
        except Exception as e:
            print(f"Error saving cache: {e}")
            
        return ticker_list
    
    print("Failed to fetch S&P 1500 tickers, falling back to default.")
    return DEFAULT_TICKERS
