import sys
import os
import time
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert 

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine
from models import Base, Stock, ScreenResult
from data_provider import HybridProvider
from screener import Screener
from symbol_loader import get_sp1500_tickers

def upsert_stock(db: Session, details: dict):
    """Update or insert stock static info."""
    symbol = details.get("symbol")
    if not symbol:
        return
        
    stock = db.query(Stock).filter(Stock.symbol == symbol).first()
    if not stock:
        stock = Stock(symbol=symbol)
        db.add(stock)
    
    stock.company_name = details.get("shortName") or details.get("longName")
    stock.sector = details.get("sector")
    stock.industry = details.get("industry")
    # last_updated is handled by onupdate
    
    return stock

def upsert_result(db: Session, details: dict):
    """Update or insert daily screen result."""
    symbol = details.get("symbol")
    calc = details.get("calculated_metrics", {})
    
    # Check if result exists for today
    today = date.today()
    result = db.query(ScreenResult).filter(
        ScreenResult.symbol == symbol,
        ScreenResult.date == today
    ).first()
    
    if not result:
        result = ScreenResult(symbol=symbol, date=today)
        db.add(result)
        
    result.score = calc.get("score")
    result.p_fcf = calc.get("p_fcf")
    result.peg_ratio = details.get("peg_ratio")
    result.market_cap = details.get("market_cap")
    result.raw_data = details

def ingest_data(limit: int = None, custom_tickers: list = None):
    print("Starting ingestion process...")
    
    # Initialize components
    provider = HybridProvider()
    screener = Screener(provider)
    
    # Get Tickers
    if custom_tickers:
        tickers = custom_tickers
    else:
        tickers = get_sp1500_tickers()
        
    if limit:
        tickers = tickers[:limit]
        
    print(f"Found {len(tickers)} tickers to process.")
    
    db = SessionLocal()
    
    # Process
    success_count = 0
    error_count = 0
    
    try:
        total = len(tickers)
        for i, ticker in enumerate(tickers):
            # Simple progress log
            if i % 10 == 0:
                print(f"Processing {i}/{total} ({ticker})...")
                
            try:
                # 1. Calculate / Fetch
                data = screener.process_ticker(ticker)
                
                if data:
                    # 2. Save to DB
                    upsert_stock(db, data)
                    upsert_result(db, data)
                    db.commit() # Commit each one to be safe/incremental
                    success_count += 1
                else:
                    # Filtered out or empty
                    pass
                    
            except Exception as e:
                print(f"Failed to process {ticker}: {e}")
                db.rollback()
                error_count += 1
                
    finally:
        db.close()
        
    print(f"Ingestion complete. Success: {success_count}, Errors: {error_count}")

if __name__ == "__main__":
    ingest_data()
