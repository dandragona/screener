from typing import List, Dict, Any, Optional
from data_provider import DataProvider, HybridProvider
from options_lib import IVEstimator
from config import MIN_MARKET_CAP, MAX_P_FCF, MAX_PEG, MIN_ROE, ENABLE_IV_RANK

class Screener:
    def __init__(self, data_provider: DataProvider):
        self.data_provider = data_provider

    def _sanitize(self, val: Any) -> Optional[Any]:
        """Sanitize values to avoid JSON serialization errors with Infinity/NaN."""
        if isinstance(val, float) and (val == float('inf') or val == float('-inf') or val != val):
            return None
        return val

    def _calculate_score(self, details: Dict[str, Any], p_fcf: float, sentiment_score: float = 0.0) -> float:
        """
        Calculate a 0-100 score based on Value, Quality, Growth, Sentiment, Volatility, and Insider signals.
        Returns a float between 0 and 100.
        """
        score = 0.0

        # --- Value Metrics (25 pts) ---
        
        # 1. P/FCF (15 pts)
        if p_fcf is not None and p_fcf != float('inf'):
            if p_fcf < 0:
                score += 0
            elif p_fcf <= 15:
                score += 15
            elif p_fcf >= 30:
                score += 0
            else:
                score += 15 - (p_fcf - 15) * (15 / 15)
        
        # 2. PEG Ratio (10 pts)
        peg = details.get("peg_ratio")
        if peg is not None:
            if peg <= 1.0:
                score += 10
            elif peg >= 2.5:
                score += 0
            else:
                score += 10 - (peg - 1.0) * (10 / 1.5)

        # --- Quality Metrics (25 pts) ---

        # 3. ROE (10 pts)
        roe = details.get("return_on_equity")
        if roe is not None:
            if roe >= 0.20:
                score += 10
            elif roe <= 0.05:
                score += 0
            else:
                score += (roe - 0.05) * (10 / 0.15)

        # 4. Operating Margins (10 pts)
        margins = details.get("operating_margins")
        if margins is not None:
             if margins >= 0.20:
                 score += 10
             elif margins <= 0.05:
                 score += 0
             else:
                 score += (margins - 0.05) * (10 / 0.15)

        # 5. Debt/Equity (5 pts)
        de = details.get("debt_to_equity")
        if de is not None:
             if de <= 0.5:
                 score += 5
             elif de >= 2.0:
                 score += 0
             else:
                 score += 5 - (de - 0.5) * (5 / 1.5)

        # --- Growth Metrics (10 pts) ---

        # 6. Analyst Upside (10 pts)
        current = details.get("current_price")
        target = details.get("target_mean")
        if current and target:
            upside = (target - current) / current
            if upside >= 0.20:
                score += 10
            elif upside <= 0:
                score += 0
            else:
                score += upside * (10 / 0.20)

        # --- Sentiment (15 pts) ---
        
        # 7. News Sentiment
        # Score ranges from -1 to 1. 
        # -1 -> 0 pts
        # 0 -> 7.5 pts
        # 1 -> 15 pts
        # Formula: (sentiment + 1) / 2 * 15
        if sentiment_score is not None:
            # Clamp between -1 and 1 just in case
            s_val = max(-1.0, min(1.0, sentiment_score))
            score += ((s_val + 1) / 2.0) * 15

        # --- Volatility (15 pts) ---

        # 8. IV Rank (10 pts)
        # Low Rank is GOOD for buying opportunities (cheap options)
        # Rank 0 -> 10 pts
        # Rank 100 -> 0 pts
        iv_rank = details.get("iv_rank")
        if iv_rank is not None:
            # iv_rank is usually 0.0 to 1.0 (or 0 to 100 ?) 
            # In data_provider/ingest it is calculated as float 0.0-1.0
            score += (1.0 - iv_rank) * 10
            
        # 9. IV < HV (5 pts)
        iv = details.get("iv_short") # Using short term as "current IV"
        hv = details.get("historical_volatility")
        if iv and hv and iv < hv:
            score += 5

        # --- Insider (10 pts) ---
            
        # 10. Insider Value (10 pts)
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
        # [NOTE] We expect sentiment_score to be in details if passed from ingest
        sentiment_score = details.get("sentiment_score", 0.0)
        score = self._calculate_score(details, p_fcf, sentiment_score)

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

    def process_ticker(self, ticker: str, fetch_mode: str = "full", sentiment_score: float = 0.0) -> Optional[Dict[str, Any]]:
        """Process a single ticker. Helper for threading/ingestion."""
        try:
            details = self.data_provider.get_ticker_details(ticker)
            
            # Inject sentiment early so it filters down
            details["sentiment_score"] = sentiment_score
            
            # --- Filter 1: Market Cap ---
            # If market cap is missing, we might filter it out or keep it.
            # For ingestion, maybe we want everything? But the user rule was Filter > 2B.
            # Let's keep the filter for now to save DB space on junk.
            if details.get("market_cap", 0) < MIN_MARKET_CAP:
                return None

            # --- Fetch Advanced Metrics (Only for filtered stocks) ---
            try:
                advanced = self.data_provider.get_advanced_metrics(ticker, include_iv_rank=ENABLE_IV_RANK, fetch_mode=fetch_mode)
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



    def get_leaps_opportunities(self, ticker: str):
        # Placeholder for options chain processing
        chain = self.data_provider.get_options_chain(ticker)
        # Logic to find IV Rank and specific LEAPs contracts will go here
        return chain
