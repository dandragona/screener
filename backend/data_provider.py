from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from typing import Dict, Any, Optional, List
import yfinance as yf
import requests
from datetime import datetime, timedelta
from config import POLYGON_API_KEY
from options_lib import IVEstimator

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

class PolygonProvider(DataProvider):
    BASE_URL = "https://api.polygon.io"

    def __init__(self):
        self.api_key = POLYGON_API_KEY

    def _get_json(self, endpoint: str, params: Dict[str, Any] = {}) -> Dict[str, Any]:
        params["apiKey"] = self.api_key
        url = f"{self.BASE_URL}{endpoint}"
        try:
            resp = requests.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Polygon API Error {url}: {e}")
            return {}

    def get_ticker_details(self, symbol: str) -> Dict[str, Any]:
        # Ticker Details v3
        details = self._get_json(f"/v3/reference/tickers/{symbol}")
        results = details.get("results", {})
        
        # Stock Snapshot for Price
        snapshot = self._get_json(f"/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}")
        snap_res = snapshot.get("ticker", {})
        
        return {
            "symbol": symbol,
            "current_price": snap_res.get("day", {}).get("c"), # Close price of current day so far
            "market_cap": results.get("market_cap"),
            "total_revenue": None, # Polygon fundys are separate endpoint
            # ... we will rely on Hybrid for these gaps
        }

    def get_options_chain(self, symbol: str) -> Dict[str, Any]:
         # Polygon options chain iteration is complex, usually we just need expirations first
         # Helper to list expirations?
         # For now, we return empty as we will use Hybrid to get chain structure if needed
         # or implement specific contract fetch later.
         return {"symbol": symbol, "expirations": []}


    def get_advanced_metrics(self, symbol: str) -> Dict[str, Any]:
        metrics = {
            "insider_net_shares": None,
            "historical_volatility": None,
            "iv_short": None,
            "iv_long": None,
            "iv_term_structure_ratio": None,
            "iv_rank": None
        }
        
        try:
            # 1. Get Current Stock Price & Details
            stock_details = self.get_ticker_details(symbol)
            curr_price = stock_details.get("current_price")
            if not curr_price:
                return metrics

            # 2. Get Expirations to find a LEAP (approx 1 year out)
            # We need to find an ATM option.
            # Polygon Options Chain API: /v3/reference/options/contracts
            # Filter: underlying_ticker=SYMBOL, expiration >= 300 days
            
            # Helper to find ATM LEAP
            params = {
                "underlying_ticker": symbol,
                "expiration_date.gte": (datetime.now() + timedelta(days=300)).strftime("%Y-%m-%d"),
                "strike_price.gte": curr_price * 0.8,
                "strike_price.lte": curr_price * 1.2,
                "limit": 10,
                "sort": "expiration_date",
                "order": "asc"
            }
            res = self._get_json("/v3/reference/options/contracts", params)
            contracts = res.get("results", [])
            
            if not contracts:
                 print(f"No LEAPs found for {symbol}")
                 return metrics
            
            # Find closest to ATM
            # Contract format: ...
            # We need the one closest to curr_price
            best_contract = min(contracts, key=lambda x: abs(x.get("strike_price") - curr_price))
            option_ticker = best_contract.get("ticker")
            strike = best_contract.get("strike_price")
            expiration = best_contract.get("expiration_date")
            
            # 3. Fetch History (1 Year) for this Option
            # We use the option price history to back-calculate IV history
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            
            # Stock History (for Underlying Price reference)
            stock_aggs = self._get_json(
                f"/v2/aggs/ticker/{symbol}/range/1/day/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}",
                {"limit": 500}
            )
            
            # Option History
            opt_aggs = self._get_json(
                 f"/v2/aggs/ticker/{option_ticker}/range/1/day/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}",
                 {"limit": 500}
            )
            
            stock_results = stock_aggs.get("results", [])
            opt_results = opt_aggs.get("results", [])
            
            # Map by date to align
            # Date is 't' (timestamp ms)
            stock_map = {r['t']: r['c'] for r in stock_results}
            
            iv_history = []
            
            # Exp date object
            exp_dt = datetime.strptime(expiration, "%Y-%m-%d")

            for bar in opt_results:
                ts = bar['t']
                if ts in stock_map:
                    s_price = stock_map[ts]
                    opt_price = bar['c']
                    
                    # Time to expiration from that date
                    date_of_bar = datetime.fromtimestamp(ts / 1000.0)
                    days_to_exp = (exp_dt - date_of_bar).days
                    if days_to_exp <= 0: continue
                    t_years = days_to_exp / 365.0
                    
                    # Calc IV
                    # Using r=0.05, Call/Put?
                    # Ticker has "C" or "P". e.g. O:TSLA230120C00100000
                    is_call = "C" in option_ticker.split(symbol)[1] # Heuristic
                    # Better: check contract type from details if available, but usually embedded.
                    # Or just assume Call if we filtered that? We didn't filter type.
                    # contracts endpoint return 'contract_type'.
                    is_call_api = best_contract.get("contract_type") == "call"
                    
                    # If it's a Call
                    if is_call_api:
                         iv = IVEstimator.impl_vol_call(opt_price, s_price, strike, t_years)
                         if iv: iv_history.append(iv)
            
            # 4. Calculate IV Rank
            if iv_history:
                low = min(iv_history)
                high = max(iv_history)
                current_iv = iv_history[-1] # Best proxy is the latest calculated
                
                # Store "Current IV" based on this method
                metrics["iv_short"] = current_iv # Actually this is long-term IV (LEAP)
                metrics["iv_long"] = current_iv
                
                if high > low:
                    metrics["iv_rank"] = (current_iv - low) / (high - low)
            
            # 5. Get Short Term IV for Term Structure (Optional for now)
            # ...
            
        except Exception as e:
            print(f"Error calculating IV Rank for {symbol}: {e}")

        return metrics

class HybridProvider(DataProvider):
    def __init__(self):
        self.yf = YFinanceProvider()
        self.poly = PolygonProvider()
        
    def get_ticker_details(self, symbol: str) -> Dict[str, Any]:
        # Merge YF (Fundys) + Polygon (Price?)
        # YF is usually good enough for fundys.
        yf_det = self.yf.get_ticker_details(symbol)
        
        # Let's trust YF for now for basics to minimize API calls unless necessary
        return yf_det

    def get_options_chain(self, symbol: str) -> Dict[str, Any]:
        return self.yf.get_options_chain(symbol)

    def get_advanced_metrics(self, symbol: str) -> Dict[str, Any]:
        # 1. Get Base Metrics from YF (Insider, HV)
        yf_metrics = self.yf.get_advanced_metrics(symbol)
        
        # 2. Enhance with Polygon (IV Rank)
        try:
            # We need Current Price for ATM and Stock History for IV Calc
            # Since Polygon Stock API is blocked, we rely on YF for stock data.
            stock_details = self.get_ticker_details(symbol)
            curr_price = stock_details.get("current_price")
            if not curr_price:
                return yf_metrics

            # A. Find ATM LEAP (Polygon)
            # Filter: underlying_ticker=SYMBOL, expiration >= 300 days
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
            res = self.poly._get_json("/v3/reference/options/contracts", params)
            contracts = res.get("results", [])
            
            
            if not contracts:
                 return yf_metrics
            
            # Find candidates closest to ATM
            # Sort by distance to strike
            candidates = sorted(contracts, key=lambda x: abs(x.get("strike_price") - curr_price))[:5] # Take top 5 closest
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            
            best_iv_history = []
            selected_contract = None
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            # Iterate candidates to find one with good history
            for contract in candidates:
                c_ticker = contract.get("ticker")
                
                # Check history count
                opt_aggs = self.poly._get_json(
                     f"/v2/aggs/ticker/{c_ticker}/range/1/day/{start_date_str}/{end_date_str}",
                     {"limit": 500}
                )
                res = opt_aggs.get("results", [])
                
                if len(res) > 20: # Threshold for "usable" history
                     # Good candidate
                     selected_contract = contract
                     opt_results = res
                     break
                
                # Keep track if we don't find any "Good" one, maybe fallback to the one with *most* data?
                if len(res) > len(best_iv_history):
                     best_iv_history = res
                     selected_contract = contract
                     opt_results = res

            if not selected_contract or not opt_results:
                 # No history found on any candidate
                 return yf_metrics

            option_ticker = selected_contract.get("ticker")
            strike = selected_contract.get("strike_price")
            expiration = selected_contract.get("expiration_date")
            is_call_api = selected_contract.get("contract_type") == "call"
            
            # Map YF History (Index is Date/datetime)
            # ...
            # We need daily close prices to match against option prices
            yf_ticker = yf.Ticker(symbol)
            hist = yf_ticker.history(start=start_date_str, end=end_date_str)
            
            iv_history = []
            exp_dt = datetime.strptime(expiration, "%Y-%m-%d")

            for bar in opt_results:
                ts = bar['t']
                dt_obj = datetime.fromtimestamp(ts / 1000.0)
                dt_str = dt_obj.strftime("%Y-%m-%d")
                
                # Find matching date in YF
                # YF index string match might be easiest
                try:
                    # Look up using string date
                    row = hist.loc[dt_str]
                    s_price = row['Close']
                except KeyError:
                    continue # Skip if no matching stock data
                
                opt_price = bar['c']
                
                # Time to expiration
                days_to_exp = (exp_dt - dt_obj).days
                if days_to_exp <= 0: continue
                t_years = days_to_exp / 365.0
                
                if is_call_api:
                     iv = IVEstimator.impl_vol_call(opt_price, s_price, strike, t_years)
                     if iv and iv > 0 and iv < 5.0: # Sanity check IV (0-500%)
                         iv_history.append(iv)
            
            # C. Calculate IV Rank
            if iv_history:
                low = min(iv_history)
                high = max(iv_history)
                current_iv = iv_history[-1]
                
                yf_metrics["iv_short"] = current_iv # Proxy
                
                if high > low:
                    yf_metrics["iv_rank"] = (current_iv - low) / (high - low)

        except Exception as e:
            print(f"Hybrid IV Error for {symbol}: {e}")
            
        return yf_metrics
