import sys
import os
import time
from datetime import date, timedelta
import asyncio
import concurrent.futures
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert 
from sqlalchemy import func, and_ 

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine
from models import Base, Stock, ScreenResult
from data_provider import HybridProvider
from screener import Screener
from symbol_loader import get_sp1500_tickers
from sentiment import SentimentService

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

def upsert_result(db: Session, details: dict, sentiment_map: dict = None):
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
    
    # Save iv30 if present
    if details.get("iv30_current"):
        result.iv30 = details.get("iv30_current")
        
    result.raw_data = details

    # [NEW] Attach Sentiment
    if sentiment_map:
        s_info = sentiment_map.get(symbol)
        if s_info:
            result.raw_data['sentiment_score'] = s_info['score']
            result.raw_data['article_count'] = s_info['count']

def upsert_history(db: Session, symbol: str, history: list):
    """Batch insert historical IV data."""
    # history is list of {'date': date_obj, 'iv30': float}
    for item in history:
        d = item['date']
        val = item['iv30']
        
        # Check existence (inefficient for bulk but safe for now)
        res = db.query(ScreenResult).filter(
            ScreenResult.symbol == symbol,
            ScreenResult.date == d
        ).first()
        
        if not res:
            res = ScreenResult(symbol=symbol, date=d)
            db.add(res)
        
        res.iv30 = val
        # We don't have other data for checking backfill, so just set iv30
    
    db.commit()

def calculate_and_save_rank(db: Session, symbol: str, result_date: date, details: dict):
    """Query DB for 1y range, calc rank, update current result."""
    start_date = result_date - timedelta(days=365)
    
    stats = db.query(
        func.min(ScreenResult.iv30),
        func.max(ScreenResult.iv30)
    ).filter(
        ScreenResult.symbol == symbol,
        ScreenResult.date >= start_date
    ).first()
    
    low, high = stats
    
    current_iv = details.get("iv30_current")
    if not current_iv:
        # Fallback to iv_short if iv30_current not set manually
        current_iv = details.get("iv_short")
        
    if current_iv and low is not None and high is not None and high > low:
        rank = (current_iv - low) / (high - low)
        details["iv_rank"] = rank # Update dict
        
        # Update DB record
        res = db.query(ScreenResult).filter(
            ScreenResult.symbol == symbol,
            ScreenResult.date == result_date
        ).first()
        if res:
            res.raw_data = details # Resave with rank
            db.commit()

def process_ticker_task(ticker: str):
    """
    Worker task to process a single ticker.
    This runs in a separate process, so we re-initialize per task 
    (or rely on fork-copy if on Linux) to ensure thread-safety of connections.
    """
    try:
        # Re-instantiate locally to avoid shared socket state issues
        # (Though requests/urllib3 are usually thread-safe, 
        #  clean slate per process is safer for heavy IO)
        provider = HybridProvider()
        screener = Screener(provider)
        return screener.process_ticker(ticker)
    except Exception as e:
        # We handle logging in the main process, but let's return the error?
        # Or just let it propagate to the future.
        raise e

def ingest_data(limit: int = None, custom_tickers: list = None, force_sentiment: bool = False):
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
        
    display_count = len(tickers)
    print(f"Found {len(tickers)} tickers to process. (Limit applied: {limit})" if limit else f"Found {len(tickers)} tickers to process.")
    
    db = SessionLocal()
    
    # [PHASE 1] Sentiment Analysis
    try:
        print("Starting Sentiment Phase...")
        sentiment_service = SentimentService(db)
        # Run async update
        asyncio.run(sentiment_service.update_sentiments(tickers[:limit] if limit else tickers, force_refresh=force_sentiment))
        
        # Pre-load sentiment map for fast lookup during data phase
        from models import StockSentiment
        # If list is huge, this IN clause might be big, but for 1500 it's fine.
        relevant_tickers = tickers[:limit] if limit else tickers
        sent_rows = db.query(StockSentiment).filter(StockSentiment.symbol.in_(relevant_tickers)).all()
        sentiment_map = {r.symbol: {'score': r.score, 'count': r.article_count} for r in sent_rows}
        print(f"Loaded {len(sentiment_map)} sentiment records.")
        
    except Exception as e:
        print(f"Sentiment Phase Failed: {e}")
        import traceback
        traceback.print_exc()
        sentiment_map = {} # Continue without sentiment
    
    # [PHASE 2] Data Phase (Parallelized)
    success_count = 0
    error_count = 0
    
    # Use ProcessPoolExecutor for CPU/IO intensive work
    # We restrict max_workers to avoid hitting rate limits too hard or overwhelming the system
    MAX_WORKERS = 4 
    
    print(f"Starting Parallel Ingestion with {MAX_WORKERS} workers...")
    
    try:
        with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submit all tasks
            future_to_ticker = {
                executor.submit(process_ticker_task, t): t 
                for t in (custom_tickers if custom_tickers else tickers)
            }
            
            total = len(future_to_ticker)
            completed = 0
            
            for future in concurrent.futures.as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                completed += 1
                
                if completed % 10 == 0:
                    print(f"Progress: {completed}/{total}...")
                
                try:
                    data = future.result()
                    
                    if data:
                        # Sequential DB Write
                        upsert_stock(db, data)
                        upsert_result(db, data, sentiment_map)
                        db.commit()
                        
                        # Rank calc requires DB read, so we do it here in main thread
                        # ensuring read-your-writes consistency
                        calculate_and_save_rank(db, ticker, date.today(), data)
                        
                        success_count += 1
                    else:
                        # Filtered or empty result
                        pass
                        
                except Exception as e:
                    print(f"Failed to process {ticker}: {e}")
                    db.rollback()
                    error_count += 1
                
    finally:
        db.close()
        
    print(f"Ingestion complete. Success: {success_count}, Errors: {error_count}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest stock data.")
    parser.add_argument("--limit", type=int, help="Limit number of tickers to process")
    parser.add_argument("--tickers", nargs="+", help="Specific tickers to process")
    parser.add_argument("--force-sentiment", action="store_true", help="Force refresh of sentiment scores")
    
    args = parser.parse_args()
    ingest_data(limit=args.limit, custom_tickers=args.tickers, force_sentiment=args.force_sentiment)
