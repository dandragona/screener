
import os
import sys
import pandas as pd
import logging
import concurrent.futures
from datetime import datetime

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_provider import PolygonProvider
from ml.dataset import DATA_DIR

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_file(file_path, provider):
    try:
        symbol = os.path.basename(file_path).replace(".parquet", "")
        df = pd.read_parquet(file_path)
        
        if len(df) < 100:
            return f"Skipped {symbol} (too short)"

        # Check if we already have populated iv30
        if 'iv30' in df.columns and df['iv30'].sum() > 0:
             # Maybe check coverage? For now skip if likely done.
             # return f"Skipped {symbol} (already has IV)"
             pass

        # Call Provider
        # Note: This is expensive/slow
        iv_data = provider.get_iv_history(symbol, df)
        
        if not iv_data:
            return f"No IV data for {symbol}"
            
        # Merge
        iv_df = pd.DataFrame(iv_data)
        iv_df['date'] = pd.to_datetime(iv_df['date'])
        
        # Ensure df index is datetime or column
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            # Left join
            df = df.merge(iv_df[['date', 'iv30']], on='date', how='left')
        else:
            # Assume index
            df = df.reset_index()
            # If renamed to something else? features.py handles it
            if 'date' not in df.columns:
                 # Try to infer or fail
                 pass
            df = df.merge(iv_df[['date', 'iv30']], on='date', how='left')
            
        # Fill NaNs? maybe ffill small gaps?
        df['iv30'] = df['iv30'].ffill(limit=5)
        
        df.to_parquet(file_path)
        return f"Updated {symbol} with {len(iv_data)} IV points"
        
    except Exception as e:
        return f"Error {symbol}: {str(e)}"

def backfill_iv():
    provider = PolygonProvider()
    files = [os.path.join(DATA_DIR, f) for f in os.listdir(DATA_DIR) if f.endswith(".parquet") and not f.startswith("macro_")]
    
    logger.info(f"Found {len(files)} files to check for IV backfill.")
    
    # Slower concurrency because of API limits
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_to_file = {executor.submit(process_file, f, provider): f for f in files}
        
        count = 0
        for future in concurrent.futures.as_completed(future_to_file):
            res = future.result()
            count += 1
            if count % 10 == 0:
                logger.info(f"Progress: {count}/{len(files)}")
                
            if "Updated" in res:
                logger.info(res)
            elif "Error" in res:
                logger.warning(res)

if __name__ == "__main__":
    backfill_iv()
