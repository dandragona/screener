
import os
import glob
import pandas as pd
import numpy as np
import xgboost as xgb
import pickle
import json
from sklearn.metrics import classification_report, precision_score, accuracy_score
from datetime import datetime
import logging

from features import FeatureEngineer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(__file__)
DATA_RAW = os.path.join(BASE_DIR, 'data', 'raw')
MODEL_DIR = os.path.join(BASE_DIR, 'models')

os.makedirs(MODEL_DIR, exist_ok=True)

class Trainer:
    def __init__(self):
        self.engineer = FeatureEngineer()
        
    def load_and_prep_data(self):
        logger.info("Loading Parquet files...")
        files = glob.glob(os.path.join(DATA_RAW, "*.parquet"))
        all_data = []
        
        # Exclude macro files
        files = [f for f in files if "macro_" not in f]
        
        count = 0
        for f in files:
            try:
                df = pd.read_parquet(f)
                if len(df) < 200: continue
                
                # Feature Eng
                df = self.engineer.generate_features(df, macro_dir=DATA_RAW)
                df = self.engineer.generate_labels(df)
                
                if not df.empty:
                    # Add symbol for tracking if needed, or just append
                    # df['symbol'] = os.path.basename(f).replace('.parquet', '')
                    all_data.append(df)
                    count += 1
                    
                if count % 100 == 0:
                    logger.info(f"Processed {count} files...")
                    
            except Exception as e:
                logger.error(f"Error prep file {f}: {e}")
                
        if not all_data:
            raise ValueError("No valid training data found!")
            
        full_df = pd.concat(all_data, ignore_index=True)
        return full_df.sort_values('date')

    def train(self):
        df = self.load_and_prep_data()
        logger.info(f"Total Training Samples: {len(df)}")
        
        # Feature columns (exclude non-feature cols)
        exclude = ['date', 'open', 'high', 'low', 'close', 'volume', 'adj_close', 
                   'target', 'fwd_ret_30d', 'z_score', 'vol_monthly', 'dividends', 'stock_splits']
                   
        feature_cols = [c for c in df.columns if c not in exclude]
        logger.info(f"Features ({len(feature_cols)}): {feature_cols}")
        
        # Walk Forward Validation
        # Split by time: Train on first 80%, Test on last 20%
        # Or proper rolling window. For simplicity start with time-series split.
        
        split_idx = int(len(df) * 0.8)
        train_df = df.iloc[:split_idx]
        test_df = df.iloc[split_idx:]
        
        X_train = train_df[feature_cols]
        y_train = train_df['target']
        X_test = test_df[feature_cols]
        y_test = test_df['target']
        
        # Model
        model = xgb.XGBClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            objective='multi:softprob',
            num_class=5,
            n_jobs=-1
        )
        
        logger.info("Training XGBoost...")
        model.fit(X_train, y_train)
        
        # Eval
        preds = model.predict(X_test)
        acc = accuracy_score(y_test, preds)
        logger.info(f"Test Accuracy: {acc:.4f}")
        logger.info("\n" + classification_report(y_test, preds))
        
        # Save Model
        model_path = os.path.join(MODEL_DIR, "xgb_classifier.pkl")
        with open(model_path, "wb") as f:
            pickle.dump(model, f)
            
        # Save Metadata (Features list)
        meta = {
            "features": feature_cols,
            "date": datetime.now().isoformat(),
            "metrics": {"accuracy": acc}
        }
        with open(os.path.join(MODEL_DIR, "meta.json"), "w") as f:
            json.dump(meta, f)
            
        logger.info(f"Model saved to {model_path}")

if __name__ == "__main__":
    trainer = Trainer()
    trainer.train()
