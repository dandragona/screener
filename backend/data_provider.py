from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import yfinance as yf
import requests
from datetime import datetime, timedelta
from config import POLYGON_API_KEY
from options_lib import IVEstimator, OptionPricingModel
from utils import retry_with_backoff
import concurrent.futures
import pandas as pd
import numpy as np

class DataProvider(ABC):
    @abstractmethod
    def get_ticker_details(self, symbol: str) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def get_options_chain(self, symbol: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_advanced_metrics(self, symbol: str, include_iv_rank: bool = True) -> Dict[str, Any]:
        pass

class YFinanceProvider(DataProvider):
    @retry_with_backoff(retries=10, backoff_in_seconds=2)
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
            "target_mean": info.get("targetMeanPrice"),
            "target_high": info.get("targetHighPrice"),
            "target_low": info.get("targetLowPrice"),
            "trailing_eps": info.get("trailingEps"),
            "forward_eps": info.get("forwardEps"),
            "debt_to_equity": info.get("debtToEquity"),
            "return_on_equity": info.get("returnOnEquity"),
            "free_cash_flow": info.get("freeCashflow"),
            "operating_margins": info.get("operatingMargins"),
            "ebitda": info.get("ebitda"),
            "total_revenue": info.get("totalRevenue"),
        }

    @retry_with_backoff(retries=10, backoff_in_seconds=2)
    def get_options_chain(self, symbol: str) -> Dict[str, Any]:
        ticker = yf.Ticker(symbol)
        expirations = ticker.options
        return {
            "symbol": symbol,
            "expirations": expirations
        }

    @retry_with_backoff(retries=10, backoff_in_seconds=2)
    def get_advanced_metrics(self, symbol: str, include_iv_rank: bool = True) -> Dict[str, Any]:
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
            purchases = ticker.insider_purchases
            if purchases is not None and not purchases.empty:
                 target_row = purchases[purchases.iloc[:, 0] == "Net Shares Purchased (Sold)"]
                 if not target_row.empty:
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
                today = datetime.now()
                exp_dates = []
                for e in expirations:
                     try:
                         d = datetime.strptime(e, "%Y-%m-%d")
                         days = (d - today).days
                         exp_dates.append((days, e))
                     except:
                         continue
                
                if exp_dates:
                    short_term = min(exp_dates, key=lambda x: abs(x[0] - 30))
                    long_term = min(exp_dates, key=lambda x: abs(x[0] - 365))
                    
                    if long_term[0] > 180: 
                        def get_atm_iv(exp_date_str):
                            opts = ticker.option_chain(exp_date_str)
                            calls = opts.calls
                            curr = hist['Close'].iloc[-1]
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

    @retry_with_backoff(retries=10, backoff_in_seconds=1, maximize_jitter=True)
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
            
    def _get_all_contracts(self, symbol: str, min_strike: float=None, max_strike: float=None) -> List[Dict[str, Any]]:
        contracts = []
        start_date = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")
        params = {
            "underlying_ticker": symbol,
            "expiration_date.gte": start_date,
            "expired": "true", # Explicitly request expired contracts
            "limit": 1000,
            "sort": "expiration_date",
            "order": "asc"
        }
        if min_strike: params["strike_price.gte"] = min_strike
        if max_strike: params["strike_price.lte"] = max_strike
        url = "/v3/reference/options/contracts"
        
        # We need to fetch both expired AND active. 
        # Polygon API might filter if expired=true is distinct from "all" or active.
        # Actually, "expired" param: "Query for expired contracts. Default is false."
        # If we set true, do we get ONLY expired?
        # Docs say: "If true, search expired options. If false, search active options."
        # So we likely need TWO loops or two requests? Or is there a way to get both?
        # Usually it's exclusive. Let's fetch expired first, then active.
        
        # 1. Fetch Expired
        self._fetch_contracts_loop(url, params.copy(), contracts, symbol)
        
        # 2. Fetch Active (remove expired param or set to false)
        active_params = params.copy()
        active_params["expired"] = "false"
        self._fetch_contracts_loop(url, active_params, contracts, symbol)
            
        return contracts

    def _fetch_contracts_loop(self, url, params, contracts, symbol):
        while True:
            res = self._get_json(url, params)
            results = res.get("results", [])
            contracts.extend(results)
            next_url = res.get("next_url")
            if next_url:
                if next_url.startswith(self.BASE_URL):
                    url = next_url[len(self.BASE_URL):]
                    params = {} 
                else: break
            else: break
            if len(contracts) > 10000: # Bump limit for safety
                print(f"Warning: Truncating contract search for {symbol} at 10000")
                break

    def get_ticker_details(self, symbol: str) -> Dict[str, Any]:
        details = self._get_json(f"/v3/reference/tickers/{symbol}")
        results = details.get("results", {})
        snapshot = self._get_json(f"/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}")
        snap_res = snapshot.get("ticker", {})
        return {
            "symbol": symbol,
            "current_price": snap_res.get("day", {}).get("c"),
            "market_cap": results.get("market_cap"),
            "total_revenue": None, 
        }

    def get_options_chain(self, symbol: str) -> Dict[str, Any]:
         return {"symbol": symbol, "expirations": []}

    def get_advanced_metrics(self, symbol: str, include_iv_rank: bool = True) -> Dict[str, Any]:
        return {}
        
    def get_current_iv(self, symbol: str, current_price: float = None) -> Optional[float]:
        """
        Calculate IV30 for the current date. Fast, lightweight.
        """
        if current_price is None:
            details = self.get_ticker_details(symbol)
            current_price = details.get("current_price")
            if not current_price: return None

        # 1. Fetch Active Contracts (~30-90 days out)
        # We don't need "all" history, just current chain.
        # But Polygon's "contracts" endpoint with "expired=false" gives us the active chain.
        # To be efficient, we can filter by expiration range directly in the API call.
        
        target_date = datetime.now() + timedelta(days=30)
        min_exp = (datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d")
        max_exp = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
        
        params = {
            "underlying_ticker": symbol,
            "expiration_date.gte": min_exp,
            "expiration_date.lte": max_exp,
            "expired": "false",
            "limit": 500,
            "sort": "expiration_date",
            "order": "asc"
        }
        
        contracts = []
        self._fetch_contracts_loop("/v3/reference/options/contracts", params, contracts, symbol)
        
        if not contracts: return None
        
        # 2. Find closest expiry to 30 days
        def parse_date(d): return datetime.strptime(d, "%Y-%m-%d")
        
        # Sort by proximity to target_date
        contracts.sort(key=lambda x: abs((parse_date(x["expiration_date"]) - target_date).days))
        best_exp = contracts[0]["expiration_date"]
        
        # Filter for best exp
        candidates = [c for c in contracts if c["expiration_date"] == best_exp]
        
        # 3. Find ATM Strike
        # Sort by proximity to current price
        candidates.sort(key=lambda x: abs(x["strike_price"] - current_price))
        if not candidates: return None
        
        best_strike = candidates[0]["strike_price"]
        atm_contracts = [c for c in candidates if c["strike_price"] == best_strike]
        
        call = next((c for c in atm_contracts if c["contract_type"] == "call"), None)
        put = next((c for c in atm_contracts if c["contract_type"] == "put"), None)
        
        if not call or not put: return None
        
        # 4. Get Current Price (Quote/Snapshot) for Option
        # We need the PREMIUM.
        # /v2/snapshot/locale/us/markets/options/tickers/{ticker}
        
        def get_price(tkr):
            snap = self._get_json(f"/v2/snapshot/locale/us/markets/options/tickers/{tkr}")
            # Try last trade, then mid of bid/ask
            day = snap.get("results", {}).get("day", {})
            if day.get("c"): return day.get("c")
            # If no trade today, maybe checking bid/ask is better, but let's stick to simple "close" or "last"
            # Actually, "lastQuote" might be better if volume is low.
            # let's trust "close" for now or "last"
            return day.get("c") # Close
            
        c_price = get_price(call["ticker"])
        p_price = get_price(put["ticker"])
        
        if not c_price or not p_price: return None
        
        t_days = (parse_date(best_exp) - datetime.now()).days
        if t_days <= 0: return None
        t_years = t_days / 365.0
        
        iv_call = IVEstimator.impl_vol_call(c_price, current_price, best_strike, t_years)
        iv_put = IVEstimator.impl_vol_put(p_price, current_price, best_strike, t_years)
        
        if iv_call and iv_put:
             return (iv_call + iv_put) / 2
        return None

    def get_iv_history(self, symbol: str, stock_history: Any) -> List[Dict[str, Any]]:
        """
        Calculate 1 year of IV history. Slow, heavy.
        Returns list of dicts: {"date": date_obj, "iv30": float}
        """
        # 1. Determine Strike Range from History
        if stock_history.empty: return []
        
        # Approximate range to reduce payload
        prices = stock_history['Close']
        low_price = prices.min()
        high_price = prices.max()
        
        # Filter contracts within 50% safety margin of 1y price range
        min_strike = low_price * 0.5
        max_strike = high_price * 1.5
        
        # 2. Fetch Contract Universe
        all_contracts = self._get_all_contracts(symbol, min_strike=min_strike, max_strike=max_strike)
        if not all_contracts: return []
            
        contracts_by_exp = {}
        for c in all_contracts:
            exp = c.get("expiration_date")
            if exp not in contracts_by_exp: contracts_by_exp[exp] = []
            contracts_by_exp[exp].append(c)
        exp_dates = sorted(contracts_by_exp.keys())
        
        # 2. Iterate each day in history
        daily_contracts = {} 
        needed_tickers = set()
        
        for date, row in stock_history.iterrows():
            stock_price = row['Close']
            current_date = pd.to_datetime(date).tz_localize(None)
            target_date = current_date + timedelta(days=30)
            
            # Find expiration closest to target_date
            valid_exps = [e for e in exp_dates if datetime.strptime(e, "%Y-%m-%d") > (current_date + timedelta(days=7))]
            if not valid_exps: continue
                
            closest_exp = min(valid_exps, key=lambda x: abs((datetime.strptime(x, "%Y-%m-%d") - target_date).days))
            candidates = contracts_by_exp[closest_exp]
            closest_contract_group = sorted(candidates, key=lambda x: abs(x.get("strike_price") - stock_price))
            
            if not closest_contract_group: continue

            best_strike = closest_contract_group[0].get("strike_price")
            call_contract = next((c for c in candidates if c.get("strike_price") == best_strike and c.get("contract_type") == "call"), None)
            put_contract = next((c for c in candidates if c.get("strike_price") == best_strike and c.get("contract_type") == "put"), None)
            
            if call_contract and put_contract:
                dt_str = current_date.strftime("%Y-%m-%d")
                daily_contracts[dt_str] = {
                    "call": call_contract.get("ticker"),
                    "put": put_contract.get("ticker"),
                    "strike": best_strike,
                    "t_days": (datetime.strptime(closest_exp, "%Y-%m-%d") - current_date).days,
                    "date_obj": current_date # Store obj for return
                }
                needed_tickers.add(call_contract.get("ticker"))
                needed_tickers.add(put_contract.get("ticker"))
                
        # 3. Batch Fetch History
        contract_histories = {} 
        def fetch_contract_history(ticker):
            end = datetime.now()
            start = end - timedelta(days=380) 
            aggs = self._get_json(
                 f"/v2/aggs/ticker/{ticker}/range/1/day/{start.strftime('%Y-%m-%d')}/{end.strftime('%Y-%m-%d')}",
                 {"limit": 500}
            )
            res = aggs.get("results", [])
            cmap = {}
            for bar in res:
                dt = datetime.fromtimestamp(bar['t'] / 1000.0).strftime("%Y-%m-%d")
                cmap[dt] = bar['c']
            return ticker, cmap

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ticker = {executor.submit(fetch_contract_history, t): t for t in needed_tickers}
            for future in concurrent.futures.as_completed(future_to_ticker):
                t, h = future.result()
                contract_histories[t] = h
                
        # 4. Calculate Daily IV
        results = []
        for date_str, info in daily_contracts.items():
            call_ticker = info['call']
            put_ticker = info['put']
            strike = info['strike']
            t_days = info['t_days']
            
            if date_str not in stock_history.index:
                try: s_price = stock_history.loc[date_str]['Close']
                except: continue
            else: s_price = stock_history.loc[date_str]['Close']
                 
            c_hist = contract_histories.get(call_ticker, {})
            p_hist = contract_histories.get(put_ticker, {})
            c_price = c_hist.get(date_str)
            p_price = p_hist.get(date_str)
            
            if c_price and p_price and t_days > 0:
                t_years = t_days / 365.0
                iv_call = IVEstimator.impl_vol_call(c_price, s_price, strike, t_years)
                iv_put = IVEstimator.impl_vol_put(p_price, s_price, strike, t_years)
                if iv_call and iv_put:
                    avg_iv = (iv_call + iv_put) / 2
                    if 0 < avg_iv < 5.0: 
                        results.append({
                            "date": info["date_obj"].strftime("%Y-%m-%d"), 
                            "iv30": avg_iv
                        })
        return results

class HybridProvider(DataProvider):
    def __init__(self):
        self.yf = YFinanceProvider()
        self.poly = PolygonProvider()
        
    def get_ticker_details(self, symbol: str) -> Dict[str, Any]:
        return self.yf.get_ticker_details(symbol)

    def get_options_chain(self, symbol: str) -> Dict[str, Any]:
        return self.yf.get_options_chain(symbol)

    def get_advanced_metrics(self, symbol: str, include_iv_rank: bool = True, fetch_mode: str = "full") -> Dict[str, Any]:
        """
        fetch_mode: 'full' (calculate history) or 'current' (today only)
        """
        yf_metrics = self.yf.get_advanced_metrics(symbol, include_iv_rank=include_iv_rank)
        try:
            if not include_iv_rank:
                return yf_metrics

            stock_details = self.get_ticker_details(symbol)
            if not stock_details: return yf_metrics
            current_price = stock_details.get("current_price")

            # Check if we need history or just current
            if fetch_mode == "current":
                current_iv = self.poly.get_current_iv(symbol, current_price)
                if current_iv:
                    yf_metrics["iv30_current"] = current_iv # Pass back to be saved
                    # We can't calc Rank without history here, but we can return the value.
                    # Rank calc must happen in Ingest or by querying DB.
            
            elif fetch_mode == "full":
                # Original logic for historical backfill
                yf_ticker = yf.Ticker(symbol)
                end_date = datetime.now()
                start_date = end_date - timedelta(days=365)
                hist = yf_ticker.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
                
                if hist.empty: return yf_metrics
                    
                iv_series_data = self.poly.get_iv_history(symbol, hist) # Returns list of dicts
                
                if iv_series_data:
                    yf_metrics["iv_history"] = iv_series_data # Pass back entire history
                    
                    # Also doing a quick local rank just in case (optional, but good for immediate display)
                    iv_values = [x["iv30"] for x in iv_series_data]
                    low = min(iv_values)
                    high = max(iv_values)
                    current = iv_values[-1]
                    
                    yf_metrics["iv_short"] = current # Legacy fields
                    yf_metrics["iv_long"] = current
                    if high > low:
                        yf_metrics["iv_rank"] = (current - low) / (high - low)
                    
        except Exception as e:
            print(f"Hybrid IV Error for {symbol}: {e}")
            import traceback
            traceback.print_exc()
        return yf_metrics
