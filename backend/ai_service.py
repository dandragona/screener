import os
import google.generativeai as genai
from typing import Dict, Any, Optional

class AIDescriptionGenerator:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("Warning: GEMINI_API_KEY not found in environment variables.")
            self.model = None
        else:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-3-flash-preview')

    def generate_description(self, ticker: str, details: Dict[str, Any]) -> str:
        if not self.model:
            return "AI analysis unavailable: API key not configured."

        try:
            # Extract key metrics for the prompt
            current_price = details.get("current_price", "N/A")
            market_cap = details.get("market_cap", "N/A")
            pe_ratio = details.get("trailing_pe", "N/A")
            forward_pe = details.get("forward_pe", "N/A")
            peg = details.get("peg_ratio", "N/A")
            p_fcf = details.get("calculated_metrics", {}).get("p_fcf", "N/A")
            roe = details.get("return_on_equity", "N/A")
            debt_to_equity = details.get("debt_to_equity", "N/A")
            operating_margins = details.get("operating_margins", "N/A")
            
            # Analyst Targets
            target_mean = details.get("target_mean", "N/A")
            target_high = details.get("target_high", "N/A")
            target_low = details.get("target_low", "N/A")
            
            # Volatility & Insider
            iv_short = details.get("iv_short", "N/A")
            iv_long = details.get("iv_long", "N/A")
            hv = details.get("historical_volatility", "N/A")
            insider = details.get("insider_net_shares", "N/A")
            
            score = details.get("calculated_metrics", {}).get("score", "N/A")
            
            prompt = f"""
            Analyze {ticker} as a potential value investment for an 8-24 month holding period.
            
            Key Financial Data:
            - Price: ${current_price}
            - Market Cap: {market_cap}
            - P/E (Trailing): {pe_ratio} (Forward: {forward_pe})
            - PEG Ratio: {peg}
            - Price/Free Cash Flow: {p_fcf}
            - ROE: {roe}
            - Operating Margins: {operating_margins}
            - Debt/Equity: {debt_to_equity}
            
            Analyst Estimates:
            - Target Mean: {target_mean} (Range: {target_low} - {target_high})
            
            Volatility & Activity:
            - Historical Volatility: {hv}
            - Implied Volatility: {iv_short} (Short) / {iv_long} (Long)
            - Net Insider Shares: {insider}
            
            Internal Score: {score}/100
            
            Provide a concise (2-3 sentences) "Buy" or "Avoid" thesis. 
            Focus on valuation, quality, and efficiency. 
            Be direct and explain WHY based on the provided numbers.
            Note: If data is missing (N/A), acknowledge that.
            """

            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Error generating AI description for {ticker}: {e}")
            return f"Error generating analysis: {str(e)}"
