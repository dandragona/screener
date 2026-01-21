
import os
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta
import logging
import concurrent.futures

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data', 'raw')
MIN_HISTORY_DAYS = 500  # Approx 2 years

class HistoryLoader:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        
    def fetch_macro_data(self):
        """Fetch VIX, SPY, and GLD data."""
        logger.info("Fetching Macro Data (VIX, SPY, GLD)...")
        tickers = ["^VIX", "SPY", "GLD"]
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365*3) # get plenty of history
        
        data = yf.download(tickers, start=start_date, end=end_date, group_by='ticker', progress=False)
        
        # Format: Multi-index columns. We want 3 separate DataFrames or one combined suited for joining.
        # Let's save them individually for easier lookups
        
        for t in tickers:
            try:
                df = data[t].copy()
                if df.empty:
                    logger.warning(f"Macro data for {t} is empty.")
                    continue
                    
                # Standardize columns
                df = df.rename(columns={"Close": "close", "Open": "open", "High": "high", "Low": "low", "Volume": "volume", "Adj Close": "adj_close"})
                df.index.name = "date"
                df = df.dropna()
                
                # Save
                safe_t = t.replace("^", "")
                save_path = os.path.join(DATA_DIR, f"macro_{safe_t}.parquet")
                df.to_parquet(save_path)
                logger.info(f"Saved macro data for {t} to {save_path}")
            except Exception as e:
                logger.error(f"Failed to process macro data {t}: {e}")

    def fetch_ticker_history(self, ticker):
        """Fetch 2y history for a single ticker."""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365*2.5) # Buffer for 2 years + indicators
            
            df = yf.download(ticker, start=start_date, end=end_date, progress=False, actions=True)
            
            if df.empty:
                return None, "Empty Data"
                
            if len(df) < MIN_HISTORY_DAYS:
                return None, f"Insufficient History ({len(df)} days)"
                
            # Quality Check: Frozen Price
            # Quality Check: Frozen Price
            # Check if close price hasn't moved for the last 5 days
            recent = df['Close'].tail(5)
            # recent.nunique() returns a scalar Series if columns are MultiIndex? 
            # No, if df is single ticker download, it might depend on yfinance format.
            # If yf.download(..., group_by='ticker') is not used for single ticker, it usually returns 1 level columns
            # unless auto_adjust is False etc.
            # Safest way:
            if isinstance(recent, pd.DataFrame):
                 # Flatten if it's a dataframe (sometimes yfinance returns DataFrame for single column if multicols)
                 # But we just want to verify if 'Close' is flat.
                 if recent.shape[1] > 1: # Should not happen for single ticker 'Close'
                     pass
                     
            uni = recent.nunique()
            # If recent is a series, uni is Int. If dataframe, it's a Series.
            if isinstance(uni, pd.Series):
                 is_frozen = (uni <= 1).all()   
            else:
                 is_frozen = (uni <= 1)
                 
            if is_frozen and len(recent) >= 5:
                 return None, "Frozen Price (Delisted/Halted)"
            
            # Standardize
            df = df.reset_index()
            # If MultiIndex columns (Price, Ticker), drop the ticker level or just take the first level
            if isinstance(df.columns, pd.MultiIndex):
                # We expect columns like (Close, AAPL), (Open, AAPL)...
                # But after reset_index, Date might be Level 0?
                # Actually, usually yf returns columns as (Attribute, Ticker). 
                # We can just drop the second level if it exists.
                df.columns = df.columns.get_level_values(0)
                
            df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
            
            # Simple validation on NaNs
            # Forward fill small gaps
            df = df.ffill(limit=3)
            if df['close'].isnull().sum() > 0:
                return None, "Too many NaNs"
                
            return df, "OK"
            
        except Exception as e:
            return None, str(e)

    def ingest_history(self, tickers):
        """Main entry point to fetch data for all tickers."""
        
        # 1. Macro Data First
        self.fetch_macro_data()
        
        logger.info(f"Starting ingestion for {len(tickers)} tickers...")
        
        success = 0
        failed = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_ticker = {executor.submit(self.fetch_ticker_history, t): t for t in tickers}
            
            for future in concurrent.futures.as_completed(future_to_ticker):
                t = future_to_ticker[future]
                try:
                    df, status = future.result()
                    if df is not None:
                        save_path = os.path.join(DATA_DIR, f"{t}.parquet")
                        df.to_parquet(save_path)
                        success += 1
                    else:
                        logger.warning(f"Skipping {t}: {status}")
                        failed += 1
                except Exception as e:
                    logger.error(f"Error processing {t}: {e}")
                    failed += 1
                    
        logger.info(f"Ingestion Complete. Success: {success}, Failed: {failed}")

if __name__ == "__main__":
    # Test run
    loader = HistoryLoader()
    # Test with a few mixed tickers
    test_tickers = ["AAPL", "GOOGL", "NONEXISTENT123", "GME"] 
    loader.ingest_history(test_tickers)
