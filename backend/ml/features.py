
import pandas as pd
import numpy as np
import os
import logging

logger = logging.getLogger(__name__)

class FeatureEngineer:
    def __init__(self):
        pass
        
    def compute_rsi(self, series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        return 100 - (100 / (1 + rs))
        
    def compute_macd(self, series, fast=12, slow=26, signal=9):
        exp1 = series.ewm(span=fast, adjust=False).mean()
        exp2 = series.ewm(span=slow, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        return macd, signal_line
        
    def compute_atr(self, df, period=14):
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        return true_range.rolling(period).mean()

    def add_macro_features(self, df, macro_dir):
        """Join VIX, SPY, GLD data to the ticker dataframe."""
        if not os.path.exists(macro_dir):
            return df
            
        for name in ["VIX", "SPY", "GLD"]:
            path = os.path.join(macro_dir, f"macro_{name}.parquet")
            if os.path.exists(path):
                macro_df = pd.read_parquet(path)
                # Ensure index is datetime
                # macro_df.index is already date from dataset.py
                
                # We only want 'close' basically, maybe 30d trend
                macro_df[f'{name}_close'] = macro_df['close']
                macro_df[f'{name}_ret_30d'] = macro_df['close'].pct_change(30)
                
                # Merge on date
                # DF index is likely RangeIndex if loaded from parquet reset, or Date?
                # Let's ensure 'date' column availability
                
                features = macro_df[[f'{name}_close', f'{name}_ret_30d']]
                
                # Check if df has date in column or index
                if 'date' in df.columns:
                     df = df.merge(features, on='date', how='left')
                else:
                    # Assume index
                     df = df.join(features)
        return df

    def generate_features(self, df, macro_dir=None):
        """
        Main method to take raw OHLCV DataFrame and return features + target.
        Expects df to have: date, open, high, low, close, volume.
        """
        # Sort just in case
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
        # 1. Price Features
        df['log_ret'] = np.log(df['close'] / df['close'].shift(1))
        
        # Lagged Returns (Momentum)
        for lag in [1, 3, 5, 10]:
            df[f'log_ret_{lag}d'] = df['log_ret'].shift(lag)
            
        df['volatility_30d'] = df['log_ret'].rolling(30).std()
        
        # Trends
        for window in [20, 50, 200]:
            df[f'ma_{window}'] = df['close'].rolling(window).mean()
            df[f'price_vs_ma_{window}'] = (df['close'] - df[f'ma_{window}']) / df[f'ma_{window}']
            
        # Momentum
        df['rsi'] = self.compute_rsi(df['close'])
        df['macd'], df['macd_sig'] = self.compute_macd(df['close'])
        df['atr'] = self.compute_atr(df) / df['close'] # Normalized ATR
        
        # Volume
        df['vol_ma_20'] = df['volume'].rolling(20).mean()
        df['vol_rel'] = df['volume'] / df['vol_ma_20']
        
        # 2. Options / Sentiment (Placeholder for now - would join from other sources)
        # Implementing basic placeholders if columns don't exist
        
        # 3. Macro
        if macro_dir:
            df = self.add_macro_features(df, macro_dir)
            
        # 4. Sector / Industry Encoding
        # Expect 'sector' column to exist from metadata merge
        if 'sector' in df.columns:
            # Simple One-Hot for top sectors? Or frequency?
            # Let's do One-Hot, but consistent columns.
            # Hardcoding common sectors to ensure alignment during inference/training
            sectors = [
                'Energy', 'Materials', 'Industrials', 'Consumer Discretionary', 
                'Consumer Staples', 'Health Care', 'Financials', 'Information Technology', 
                'Communication Services', 'Utilities', 'Real Estate'
            ]
            for s in sectors:
                # Create boolean column
                # Use str.contains to match "Information Technology" etc
                # Be careful with case
                col_name = f"sector_{s.lower().replace(' ', '_')}"
                df[col_name] = (df['sector'] == s).astype(int)
                
            # Drop raw columns
            df = df.drop(columns=['sector', 'industry'], errors='ignore')
        
        # Drop rows with NaNs created by Lags (max lag 10, rolling 200...)
        return df.dropna()

    def generate_labels(self, df):
        """
        Create 5-class target based on 30d fwd return Z-Score.
        """
        # Forward Return
        df['fwd_ret_30d'] = df['close'].shift(-30) / df['close'] - 1
        
        # Volatility adjusted denominator
        # We use current rolling vol as the normalizer
        # Annualized Vol = vol_30d * sqrt(252). Monthly vol = vol_30d * sqrt(21)
        # Let's stick to the period duration: 30 days ~ 21 trading days.
        
        df['vol_monthly'] = df['volatility_30d'] * np.sqrt(21)
        
        # Avoid div by zero
        df['vol_monthly'] = df['vol_monthly'].replace(0, np.nan)
        
        df['z_score'] = df['fwd_ret_30d'] / df['vol_monthly']
        
        # Binning
        # Class 0 (Large Neg): Z < -1.5
        # Class 1 (Small Neg): -1.5 <= Z < -0.5
        # Class 2 (Neutral): -0.5 <= Z <= 0.5
        # Class 3 (Small Pos): 0.5 < Z <= 1.5
        # Class 4 (Large Pos): Z > 1.5
        
        conditions = [
            (df['z_score'] < -1.5),
            (df['z_score'] >= -1.5) & (df['z_score'] < -0.5),
            (df['z_score'] >= -0.5) & (df['z_score'] <= 0.5),
            (df['z_score'] > 0.5) & (df['z_score'] <= 1.5),
            (df['z_score'] > 1.5)
        ]
        choices = [0, 1, 2, 3, 4]
        
        df['target'] = np.select(conditions, choices, default=-1)
        
        # Drop rows where target cannot be computed (last 30 days)
        valid_df = df[df['target'] != -1].copy()
        
        return valid_df

