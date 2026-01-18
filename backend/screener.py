from typing import List, Dict, Any, Optional
from data_provider import DataProvider, HybridProvider
from options_lib import IVEstimator
from config import MIN_MARKET_CAP, MAX_P_FCF, MAX_PEG, MIN_ROE

class Screener:
    def __init__(self, data_provider: DataProvider):
        self.data_provider = data_provider

    def _sanitize(self, val: Any) -> Optional[Any]:
        """Sanitize values to avoid JSON serialization errors with Infinity/NaN."""
        if isinstance(val, float) and (val == float('inf') or val == float('-inf') or val != val):
            return None
        return val

    def _calculate_score(self, details: Dict[str, Any], p_fcf: float) -> float:
        """
        Calculate a 0-100 score based on Value, Quality, Growth, and Volatility/Insider signals.
        Returns a float between 0 and 100.
        """
        score = 0.0

        # --- Value Metrics (30 pts) ---
        
        # 1. P/FCF (15 pts) - Reduced from 20
        # 0 pts if > 30, 15 pts if < 15
        if p_fcf is not None and p_fcf != float('inf'):
            if p_fcf < 0:
                score += 0
            elif p_fcf <= 15:
                score += 15
            elif p_fcf >= 30:
                score += 0
            else:
                # Linear interpolation: 15 -> 0 as p_fcf 15 -> 30
                # Slope = -15 / 15 = -1.0
                score += 15 - (p_fcf - 15) * (15 / 15)
        
        # 2. PEG Ratio (15 pts) - Reduced from 20
        # 0 pts if > 2.5, 15 pts if < 1.0
        peg = details.get("peg_ratio")
        if peg is not None:
            if peg <= 1.0:
                score += 15
            elif peg >= 2.5:
                score += 0
            else:
                # Linear: 15 -> 0 as peg 1.0 -> 2.5
                score += 15 - (peg - 1.0) * (15 / 1.5)

        # --- Quality Metrics (35 pts) ---

        # 3. ROE (15 pts) - Reduced from 20
        # 0 pts if < 5%, 15 pts if > 20%
        roe = details.get("return_on_equity")
        if roe is not None:
            if roe >= 0.20:
                score += 15
            elif roe <= 0.05:
                score += 0
            else:
                # Linear: 0 -> 15 as roe 0.05 -> 0.20
                score += (roe - 0.05) * (15 / 0.15)

        # 4. Operating Margins (10 pts)
        # 0 pts if < 5%, 10 pts if > 20%
        margins = details.get("operating_margins")
        if margins is not None:
             if margins >= 0.20:
                 score += 10
             elif margins <= 0.05:
                 score += 0
             else:
                 score += (margins - 0.05) * (10 / 0.15)

        # 5. Debt/Equity (10 pts)
        # 0 pts if > 2.0, 10 pts if < 0.5
        de = details.get("debt_to_equity")
        if de is not None:
             if de <= 0.5:
                 score += 10
             elif de >= 2.0:
                 score += 0
             else:
                 score += 10 - (de - 0.5) * (10 / 1.5)

        # --- Growth Metrics (15 pts) ---

        # 6. Analyst Upside (15 pts) - Reduced from 20
        # 0 pts if < 0% upside, 15 pts if > 20% upside
        current = details.get("current_price")
        target = details.get("target_mean")
        if current and target:
            upside = (target - current) / current
            if upside >= 0.20:
                score += 15
            elif upside <= 0:
                score += 0
            else:
                score += upside * (15 / 0.20)

        # --- New Metrics (20 pts) ---

        # 7. Cheap Volatility (10 pts)
        # IV < HV (+5)
        # Term Structure Ratio < 1.1 (+5)
        iv = details.get("iv_short") # Using short term as "current IV"
        hv = details.get("historical_volatility")
        ratio = details.get("iv_term_structure_ratio")
        
        if iv and hv and iv < hv:
            score += 5
            
        if ratio and ratio < 1.1:
            score += 5
            
        # 8. Insider Value (10 pts)
        # Net Insider Buying > 0 (+10)
        net_insider = details.get("insider_net_shares")
        if net_insider and net_insider > 0:
            score += 10

        return min(100.0, max(0.0, score))

    def _calculate_metrics(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate derived metrics like P/FCF and enhance details."""
        fcf = details.get("free_cash_flow")
        market_cap = details.get("market_cap")
        
        # Calculate P/FCF
        p_fcf = (market_cap / fcf) if fcf else float('inf')
        
        # Calculate Score
        score = self._calculate_score(details, p_fcf)

        details["calculated_metrics"] = {
            "p_fcf": self._sanitize(p_fcf),
            "score": score
        }
        
        # Sanitize other fields
        details["peg_ratio"] = self._sanitize(details.get("peg_ratio"))
        details["debt_to_equity"] = self._sanitize(details.get("debt_to_equity"))
        details["return_on_equity"] = self._sanitize(details.get("return_on_equity"))
        details["operating_margins"] = self._sanitize(details.get("operating_margins"))
        details["target_mean"] = self._sanitize(details.get("target_mean"))
        details["target_high"] = self._sanitize(details.get("target_high"))
        details["target_low"] = self._sanitize(details.get("target_low"))
        
        # Sanitize new fields
        details["historical_volatility"] = self._sanitize(details.get("historical_volatility"))
        details["iv_short"] = self._sanitize(details.get("iv_short"))
        details["iv_long"] = self._sanitize(details.get("iv_long"))
        details["iv_term_structure_ratio"] = self._sanitize(details.get("iv_term_structure_ratio"))
        details["insider_net_shares"] = self._sanitize(details.get("insider_net_shares"))
        
        return details

    def screen_stocks(self, tickers: List[str]) -> List[Dict[str, Any]]:
        results = []
        import concurrent.futures

        def process_ticker(ticker: str) -> Optional[Dict[str, Any]]:
            try:
                details = self.data_provider.get_ticker_details(ticker)
                
                # --- Filter 1: Market Cap ---
                if details.get("market_cap", 0) < MIN_MARKET_CAP:
                    return None

                # --- Fetch Advanced Metrics (Only for filtered stocks) ---
                try:
                    advanced = self.data_provider.get_advanced_metrics(ticker)
                    if advanced:
                        details.update(advanced)
                except Exception as adv_err:
                    print(f"Warning: Could not fetch advanced metrics for {ticker}: {adv_err}")

                # --- Calculate Metrics & Score ---
                details = self._calculate_metrics(details)
                return details

            except Exception as e:
                print(f"Error screening {ticker}: {e}")
                return None

        # Use efficient parallel processing
        # Use efficient parallel processing
        # Adjust max_workers based on expected load. heavy rate limiting observed with 20.
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_ticker = {executor.submit(process_ticker, ticker): ticker for ticker in tickers}
            for future in concurrent.futures.as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                try:
                    data = future.result()
                    if data:
                        results.append(data)
                except Exception as exc:
                    print(f"Generated an exception for {ticker}: {exc}")
                
        # Sort by score
        return sorted(results, key=lambda x: x["calculated_metrics"]["score"], reverse=True)

    def get_leaps_opportunities(self, ticker: str):
        # Placeholder for options chain processing
        chain = self.data_provider.get_options_chain(ticker)
        # Logic to find IV Rank and specific LEAPs contracts will go here
        return chain
