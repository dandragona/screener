
import yfinance as yf
try:
    ticker = yf.Ticker("NVDA")
    purchases = ticker.insider_purchases
    print("Purchases found:")
    print(purchases)
    if purchases is not None and not purchases.empty:
        target_row = purchases[purchases.iloc[:, 0] == "Net Shares Purchased (Sold)"]
        print("Target Row:")
        print(target_row)
        if not target_row.empty:
            print("Value:", float(target_row.iloc[0, 1]))
        else:
            print("Target row empty")
    else:
        print("Purchases empty or None")
except Exception as e:
    print(f"Error: {e}")
