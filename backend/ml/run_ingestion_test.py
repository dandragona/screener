
import os
import sys
import pandas as pd
import logging
import glob

# Add backend directory to path to import modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from ml.dataset import HistoryLoader, DATA_DIR
from ml.features import FeatureEngineer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    # 1. Setup
    loader = HistoryLoader()
    fe = FeatureEngineer()
    
    # 2. Define subset
    subset_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'SPY', 'IWM', 'QQQ', 'GLD', 'VXX']
    logger.info(f"Running ingestion for subset: {subset_tickers}")
    
    # 3. Ingest
    loader.ingest_history(subset_tickers)
    
    # 4. Load and Process
    logger.info("Processing ingested data...")
    all_data = []
    
    # Reload macro data path
    macro_dir = DATA_DIR
    
    for ticker in subset_tickers:
        file_path = os.path.join(DATA_DIR, f"{ticker}.parquet")
        if not os.path.exists(file_path):
            logger.warning(f"File for {ticker} not found. Skipping.")
            continue
            
        try:
            df = pd.read_parquet(file_path)
            
            # Generate Features
            df = fe.generate_features(df, macro_dir=macro_dir)
            
            # Generate Labels
            df = fe.generate_labels(df)
            
            if not df.empty:
                df['ticker'] = ticker # Add ticker identifier
                all_data.append(df)
                logger.info(f"Processed {ticker}: {len(df)} rows")
            else:
                logger.warning(f"{ticker} resulted in empty dataframe after processing.")
                
        except Exception as e:
            logger.error(f"Failed to process {ticker}: {e}")
            
    # 5. Concatenate and Dump
    if all_data:
        full_df = pd.concat(all_data)
        
        # Create processed dir if not exists
        processed_dir = os.path.join(os.path.dirname(__file__), 'data', 'processed')
        os.makedirs(processed_dir, exist_ok=True)
        
        output_path = os.path.join(processed_dir, 'training_data.csv')
        full_df.to_csv(output_path)
        logger.info(f"Saved processed data to {output_path}")
        
        # 6. Audit
        print("\n" + "="*30)
        print("DATA AUDIT")
        print("="*30)
        print(f"Total Rows: {len(full_df)}")
        print(f"Total Columns: {len(full_df.columns)}")
        print(f"Columns: {list(full_df.columns)}")
        print("\nMissing Values:")
        print(full_df.isnull().sum()[full_df.isnull().sum() > 0])
        print("\nTarget Distribution:")
        print(full_df['target'].value_counts().sort_index())
        print("\nRows per Ticker:")
        print(full_df['ticker'].value_counts())
        print("="*30 + "\n")
        
    else:
        logger.error("No data collected!")

if __name__ == "__main__":
    main()
