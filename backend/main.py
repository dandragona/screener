from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import List, Optional
from data_provider import YFinanceProvider
from screener import Screener
from ai_service import AIDescriptionGenerator
from config import DEFAULT_TICKERS, API_TITLE, API_HOST, API_PORT
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = FastAPI(title=API_TITLE)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize dependencies
from data_provider import HybridProvider
data_provider = HybridProvider()
screener = Screener(data_provider)
ai_generator = AIDescriptionGenerator()

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/screen")
def screen_stocks(tickers: Optional[List[str]] = Query(None)):
    """
    Screen a list of stocks based on Value & Quality criteria.
    If no tickers provided, uses the Russell 2000 list.
    """
    if tickers:
        target_tickers = tickers
    else:
        # Load S&P 1500
        from symbol_loader import get_sp1500_tickers
        target_tickers = get_sp1500_tickers()
    
    results = screener.screen_stocks(target_tickers)
    return results

@app.get("/ticker/{symbol}")
def get_ticker_details(symbol: str):
    try:
        return data_provider.get_ticker_details(symbol)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/options/{symbol}")
def get_options_chain(symbol: str):
    try:
        return data_provider.get_options_chain(symbol)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/analyze/{symbol}")
def analyze_stock(symbol: str):
    """
    Generate an AI-powered analysis for a specific stock.
    """
    try:
        # Fetch fresh details for the analysis
        details = data_provider.get_ticker_details(symbol)
        
        # Use screener to calculate metrics consistently
        # Note: We might want to make calculate_metrics public or accessible if we want to reuse it here
        # For now, we reuse the private method logic via a helper or just rely on what we can get.
        # Ideally, we should refactor Screener to have a public `enrich_data` method.
        # But per current refactor plan, I'll stick to a simple clean up.
        
        # We can actually use the screener to get the enriched details if we passed a list of one
        # but that might be overkill. Let's just use the logic we have or instantiate a screener helper.
        # For this refactor, let's keep it simple and just let the AI service handle the raw details 
        # or calculate what's missing if critical.
        
        # Actually, let's just do a quick calculation here or if we want to be DRY, use the screener.
        # Let's use the screener's _calculate_metrics by making it public or using it via a list call.
        
        # Let's fix the screener to have a public method for single items in a future step if needed.
        # For now, we will duplicate the small calculation or just pass raw data.
        # The AI service prompts asks for P/FCF, so we should calculate it.
        
        fcf = details.get("free_cash_flow")
        market_cap = details.get("market_cap")
        p_fcf = (market_cap / fcf) if fcf and fcf > 0 else None
        
        if "calculated_metrics" not in details:
            details["calculated_metrics"] = {}
        details["calculated_metrics"]["p_fcf"] = p_fcf
        
        analysis = ai_generator.generate_description(symbol, details)
        return {"symbol": symbol, "analysis": analysis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host=API_HOST, port=API_PORT, reload=True)
