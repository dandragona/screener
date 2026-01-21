
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
            recent = df['Close'].tail(5)
            
            # Robust check using numpy to avoid DataFrame/Series ambiguity
            # Take values, flatten, check uniqueness
            vals = recent.values.flatten()
            # Filter out NaNs just in case, though tail(5) from filled data might be safe, but here raw data
            vals = vals[~np.isnan(vals)]
            
            if len(vals) >= 5:
                unique_count = len(np.unique(vals))
                if unique_count <= 1:
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
            
            # Deduplicate columns (keep first occurrence)
            df = df.loc[:, ~df.columns.duplicated()]
            
            # Simple validation on NaNs
            # Forward fill small gaps
            df = df.ffill(limit=3)
            # Use numpy sum to avoid Series ambiguity if 'close' is a DataFrame
            # (which can happen if column renaming collapsed duplicates improperly)
            nan_count = np.sum(df['close'].isnull().values)
            if nan_count > 0:
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

    def merge_metadata(self):
        """
        Merge Sector/Industry data into existing Parquet files.
        """
        sector_map_path = os.path.join(os.path.dirname(DATA_DIR), "..", "..", "data", "sp1500_sectors.csv")
        if not os.path.exists(sector_map_path):
            logger.warning("Sector map not found. Run symbol_loader first.")
            return
            
        try:
            meta_df = pd.read_csv(sector_map_path)
            # Create a dict for fast lookup: Symbol -> (Sector, Industry)
            meta_dict = meta_df.set_index('Symbol')[['Sector', 'Industry']].to_dict('index')
            
            files = [f for f in os.listdir(DATA_DIR) if f.endswith(".parquet") and not f.startswith("macro_")]
            logger.info(f"Merging metadata for {len(files)} files...")
            
            count = 0
            for f in files:
                path = os.path.join(DATA_DIR, f)
                symbol = f.replace(".parquet", "")
                
                if symbol in meta_dict:
                    try:
                        df = pd.read_parquet(path)
                        # Avoid overwriting if unnecessary, but here we just set it
                        info = meta_dict[symbol]
                        
                        # Set as categorical to save space or string
                        # Creating a column with the same value for all rows
                        df['sector'] = info.get('Sector', 'Unknown')
                        df['industry'] = info.get('Industry', 'Unknown')
                        
                        df.to_parquet(path)
                        count += 1
                    except Exception as e:
                        logger.error(f"Error updating {f}: {e}")
                        
            logger.info(f"Updated {count} files with metadata.")
            
        except Exception as e:
            logger.error(f"Failed to load sector map: {e}")

if __name__ == "__main__":
    # Test run
    loader = HistoryLoader()
    # Test with a few mixed tickers
    # test_tickers = ["AAPL", "GOOGL", "NONEXISTENT123", "GME"] 
    # loader.ingest_history(test_tickers)
    
    # Run metadata merge if executed directly
    loader.merge_metadata()
