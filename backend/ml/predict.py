
import os
import pickle
import json
import pandas as pd
import logging
from .features import FeatureEngineer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'xgb_classifier.pkl')
META_PATH = os.path.join(BASE_DIR, 'models', 'meta.json')
DATA_RAW = os.path.join(BASE_DIR, 'data', 'raw')

class Predictor:
    def __init__(self):
        self.model = None
        self.features = []
        self.engineer = FeatureEngineer()
        self.load_model()
        
    def load_model(self):
        if not os.path.exists(MODEL_PATH) or not os.path.exists(META_PATH):
            logger.warning("ML Model not found. Predictions will be disabled.")
            return

        try:
            with open(MODEL_PATH, "rb") as f:
                self.model = pickle.load(f)
            
            with open(META_PATH, "r") as f:
                meta = json.load(f)
                self.features = meta.get("features", [])
        except Exception as e:
            logger.error(f"Failed to load ML model: {e}")
            self.model = None

    def predict_one(self, ticker, price_history_df):
        """
        Run inference for a single stock.
        price_history_df: DataFrame with OHLCV data (daily).
        """
        if self.model is None or price_history_df.empty:
            return None, 0.0
            
        try:
            # Prepare Data (Engineer features)
            # We assume price_history_df is already standard columns (open, high, low, close, volume, date)
            # Just verify lowercase
            df = price_history_df.copy()
            df.columns = [c.lower() for c in df.columns]
            
            # Feature Gen
            # We point to local raw dir for macro if available
            df = self.engineer.generate_features(df, macro_dir=DATA_RAW)
            
            if df.empty: return None, 0.0
            
            # Take last row
            latest = df.iloc[[-1]] 
            
            # Check missing features
            missing = [c for c in self.features if c not in latest.columns]
            if missing:
                # Naive fill 0? Or return None?
                # For robustness, fill 0
                for c in missing: latest[c] = 0
                
            X = latest[self.features]
            
            # Predict
            # Classes: 0..4
            # 0: Large Neg, 4: Large Pos
            prob = self.model.predict_proba(X)[0]
            pred_class = self.model.predict(X)[0]
            
            confidence = prob[pred_class]
            
            # Map class to string
            labels = ["Large Negative", "Small Negative", "Neutral", "Small Positive", "Large Positive"]
            label = labels[pred_class]
            
            return label, float(confidence)
            
        except Exception as e:
            logger.error(f"Prediction failed for {ticker}: {e}")
            return None, 0.0
