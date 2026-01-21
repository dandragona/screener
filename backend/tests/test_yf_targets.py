
import yfinance as yf

def test_yfinance_targets(ticker):
    print(f"Fetching data for {ticker}...")
    try:
        t = yf.Ticker(ticker)
        info = t.info
        
        print("\n--- Price Targets ---")
        print(f"Target High: {info.get('targetHighPrice')}")
        print(f"Target Low: {info.get('targetLowPrice')}")
        print(f"Target Mean: {info.get('targetMeanPrice')}")
        print(f"Target Median: {info.get('targetMedianPrice')}")
        print(f"Number of Analysts: {info.get('numberOfAnalystOpinions')}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_yfinance_targets("AAPL")
