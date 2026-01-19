from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
import uvicorn
from typing import List, Optional, Any
import json
from datetime import date

# Local imports
from database import get_db
from models import ScreenResult, Stock
from data_provider import HybridProvider
from ai_service import AIDescriptionGenerator
from config import API_TITLE, API_HOST, API_PORT
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

# Initialize data provider for detail views (live data for specific ticker)
# We keep this for /ticker/{symbol} which might want fresh real-time price/options
data_provider = HybridProvider()
ai_generator = AIDescriptionGenerator()

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/screen")
def screen_stocks(
    tickers: Optional[List[str]] = Query(None),
    min_score: float = 0.0,
    min_market_cap: float = 0.0,
    sector: Optional[str] = None,
    limit: int = 2000,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Get screened stocks from the database.
    Results are pre-calculated daily.
    """
    # Find the latest date in results
    latest_date_query = db.query(func.max(ScreenResult.date)).scalar()
    
    if not latest_date_query:
        return [] # No data yet

    query = db.query(ScreenResult).join(Stock).filter(ScreenResult.date == latest_date_query)

    # Filter by Tickers
    if tickers:
        query = query.filter(ScreenResult.symbol.in_(tickers))

    # filter by score
    if min_score > 0:
        query = query.filter(ScreenResult.score >= min_score)

    # Filter by Market Cap
    if min_market_cap > 0:
        # Note: market_cap is stored in ScreenResult, or we can filter via raw_data or Stock?
        # We added market_cap column to ScreenResult for this purpose in Phase 1
        query = query.filter(ScreenResult.market_cap >= min_market_cap)

    # Filter by Sector
    if sector:
        query = query.filter(Stock.sector == sector)

    # Sort by Score DESC
    query = query.order_by(desc(ScreenResult.score))
    
    # Pagination
    results = query.offset(offset).limit(limit).all()
    
    # Return raw_data (the JSON blob which matches the old API format)
    return [r.raw_data for r in results]

@app.get("/ticker/{symbol}")
def get_ticker_details(symbol: str):
    try:
        # We can still fetch live data for details view
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
def analyze_stock(symbol: str, db: Session = Depends(get_db)):
    """
    Generate an AI-powered analysis for a specific stock using the latest screened data.
    """
    try:
        # Find the latest date in results
        # We could optimize this to just get the latest result for this symbol directly if we assume dates are consistent,
        # but matching the /screen logic (latest_date_query) ensures we use the same "batch".
        # However, for a specific symbol, we just want the most recent data available.
        
        result = db.query(ScreenResult).filter(
            ScreenResult.symbol == symbol
        ).order_by(desc(ScreenResult.date)).first()
        
        if not result or not result.raw_data:
             raise HTTPException(status_code=404, detail=f"No screened data found for {symbol}")
        
        details = result.raw_data
        
        # Calculate basic metrics if missing (though they should be in raw_data from ingestion)
        # We can keep this fallback logic just in case ingestion didn't calc it or it's old data
        if "calculated_metrics" not in details:
             details["calculated_metrics"] = {}
             
        # Ensure p_fcf is there if needed
        fcf = details.get("free_cash_flow")
        market_cap = details.get("market_cap")
        if "p_fcf" not in details["calculated_metrics"]:
             p_fcf = (market_cap / fcf) if fcf and fcf > 0 else None
             details["calculated_metrics"]["p_fcf"] = p_fcf
        
        analysis = ai_generator.generate_description(symbol, details)
        return {"symbol": symbol, "analysis": analysis}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host=API_HOST, port=API_PORT, reload=True)
