from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import yfinance as yf

class DataProvider(ABC):
    @abstractmethod
    def get_ticker_details(self, symbol: str) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def get_options_chain(self, symbol: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_advanced_metrics(self, symbol: str) -> Dict[str, Any]:
        pass

class YFinanceProvider(DataProvider):
    def get_ticker_details(self, symbol: str) -> Dict[str, Any]:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return {
            "symbol": symbol,
            "current_price": info.get("currentPrice"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "peg_ratio": info.get("pegRatio") or info.get("trailingPegRatio"),
            "price_to_book": info.get("priceToBook"),
            "fifty_day_average": info.get("fiftyDayAverage"),
            "two_hundred_day_average": info.get("twoHundredDayAverage"),
            "beta": info.get("beta"),
            # Price Targets
            "target_mean": info.get("targetMeanPrice"),
            "target_high": info.get("targetHighPrice"),
            "target_low": info.get("targetLowPrice"),
            # Value/Quality metrics
            "trailing_eps": info.get("trailingEps"),
            "forward_eps": info.get("forwardEps"),
            "debt_to_equity": info.get("debtToEquity"),
            "return_on_equity": info.get("returnOnEquity"),
            "free_cash_flow": info.get("freeCashflow"),
            "operating_margins": info.get("operatingMargins"),
            "ebitda": info.get("ebitda"),
            "total_revenue": info.get("totalRevenue"),
        }

    def get_options_chain(self, symbol: str) -> Dict[str, Any]:
        ticker = yf.Ticker(symbol)
        expirations = ticker.options
        return {
            "symbol": symbol,
            "expirations": expirations
        }

    def get_advanced_metrics(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch advanced metrics for LEAPs screening:
        1. Insider Buying (Net Shares)
        2. Historical Volatility (1 Year)
        3. IV Term Structure (Short vs Long term IV)
        """
        import numpy as np
        import pandas as pd
        
        ticker = yf.Ticker(symbol)
        metrics = {
            "insider_net_shares": None,
            "historical_volatility": None,
            "iv_short": None,
            "iv_long": None,
            "iv_term_structure_ratio": None
        }

        # 1. Insider Buying
        try:
            # Try 6 month window of purchases/sales
            # YF often returns a dataframe 'insider_purchases' or 'insider_transactions'
            # We'll try to calculate net manually if structure allows, or safe default
            # Actually YF 'insider_purchases' gives a summary which is easier
            purchases = ticker.insider_purchases
            if purchases is not None and not purchases.empty:
                 # Look for 'Net Shares Purchased (Sold)' row
                 # Typical format has "Insider Purchases Last 6m" as index or column
                 # Based on spike output:
                 # 0                      Purchases
                 # 1                          Sales
                 # 2    Net Shares Purchased (Sold)
                 # We need to find the row with "Net Shares Purchased (Sold)"
                 
                 # It seems purchases is a dataframe where the first column acts like a label
                 # Let's assume standard YF dataframe structure from spike
                 target_row = purchases[purchases.iloc[:, 0] == "Net Shares Purchased (Sold)"]
                 if not target_row.empty:
                     # Access the 'Shares' column (col 1)
                     metrics["insider_net_shares"] = float(target_row.iloc[0, 1])
        except Exception as e:
            print(f"Error fetching insider data for {symbol}: {e}")

        # 2. Historical Volatility
        try:
            hist = ticker.history(period="1y")
            if not hist.empty and len(hist) > 200:
                hist['Log_Ret'] = np.log(hist['Close'] / hist['Close'].shift(1))
                daily_std = hist['Log_Ret'].std()
                metrics["historical_volatility"] = daily_std * np.sqrt(252)
        except Exception as e:
            print(f"Error fetching HV for {symbol}: {e}")

        # 3. IV Term Structure
        try:
            expirations = ticker.options
            if expirations and len(expirations) > 1:
                # Short term: ~30 days (closest to month 1)
                # Long term: ~365 days (closest to year 1)
                
                # Simple approximation: index 1 (approx 1-4 weeks) or search dates
                # Let's try to find an expiration ~30 days out and ~365 days out
                from datetime import datetime
                today = datetime.now()
                
                # Convert exp strings to dates
                exp_dates = []
                for e in expirations:
                     try:
                         # YF format YYYY-MM-DD
                         d = datetime.strptime(e, "%Y-%m-%d")
                         days = (d - today).days
                         exp_dates.append((days, e))
                     except:
                         continue
                
                if exp_dates:
                    # Find closest to 30
                    short_term = min(exp_dates, key=lambda x: abs(x[0] - 30))
                    # Find closest to 365 (must be at least 180 to be useful)
                    long_term = min(exp_dates, key=lambda x: abs(x[0] - 365))
                    
                    if long_term[0] > 180: # Ensure it's actually long term
                        # Fetch chains
                        # Note: option_chain() fetches both calls and puts. 
                        # We use ATM calls for IV proxy.
                        
                        def get_atm_iv(exp_date_str):
                            opts = ticker.option_chain(exp_date_str)
                            calls = opts.calls
                            
                            # Find ATM strike
                            # Need current price. If we don't have it handy, use history last close
                            # But we usually have it. Let's assume we can get it from hist or info
                            # Using hist last close is faster than refetching info
                            curr = hist['Close'].iloc[-1]
                            
                            # Find strike closest to curr
                            # Filter for valid IVs
                            calls = calls[calls['impliedVolatility'] > 0]
                            if calls.empty: return None
                            
                            closest_row = calls.iloc[(calls['strike'] - curr).abs().argsort()[:1]]
                            if not closest_row.empty:
                                return closest_row.iloc[0]['impliedVolatility']
                            return None

                        metrics["iv_short"] = get_atm_iv(short_term[1])
                        metrics["iv_long"] = get_atm_iv(long_term[1])
                        
                        if metrics["iv_short"] and metrics["iv_long"]:
                            metrics["iv_term_structure_ratio"] = metrics["iv_long"] / metrics["iv_short"]

        except Exception as e:
            print(f"Error fetching options IV for {symbol}: {e}")

        return metrics
