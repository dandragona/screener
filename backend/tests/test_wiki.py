import pandas as pd
import httpx
from io import StringIO

def fetch_sp_index(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = httpx.get(url, headers=headers)
    response.raise_for_status()
    # Wrap in StringIO for pandas
    return pd.read_html(StringIO(response.text))[0]

def test_fetch():
    try:
        print("Fetching S&P 500...")
        sp500 = fetch_sp_index("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
        print(f"S&P 500 count: {len(sp500)}")
        
        print("Fetching S&P 400...")
        sp400 = fetch_sp_index("https://en.wikipedia.org/wiki/List_of_S%26P_400_companies")
        print(f"S&P 400 count: {len(sp400)}")
        
        print("Fetching S&P 600...")
        sp600 = fetch_sp_index("https://en.wikipedia.org/wiki/List_of_S%26P_600_companies")
        print(f"S&P 600 count: {len(sp600)}")
        
        total = len(sp500) + len(sp400) + len(sp600)
        print(f"Total S&P 1500 count: {total}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_fetch()
