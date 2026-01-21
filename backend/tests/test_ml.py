
import pytest
import pandas as pd
import numpy as np
import os
from unittest.mock import MagicMock, patch
from backend.ml.features import FeatureEngineer
from backend.ml.dataset import HistoryLoader

@pytest.fixture
def sample_ohlcv():
    # Create a dummy 300-day OHLCV dataframe (needs to be > 200 for MA_200)
    dates = pd.date_range(end=pd.Timestamp.now(), periods=300)
    data = {
        'date': dates,
        'open': np.linspace(100, 110, 300),
        'high': np.linspace(101, 111, 300),
        'low': np.linspace(99, 109, 300),
        'close': np.linspace(100, 110, 300) + np.random.normal(0, 1, 300),
        'volume': np.random.randint(1000, 5000, 300)
    }
    df = pd.DataFrame(data)
    # Add some trend to verify indicators
    df.loc[150:, 'close'] = df.loc[150:, 'close'] * 1.05
    return df

class TestFeatureEngineer:
    def test_indicators_structural_integrity(self, sample_ohlcv):
        eng = FeatureEngineer()
        df = eng.generate_features(sample_ohlcv)
        
        # Check columns exist
        expected = ['rsi', 'macd', 'macd_sig', 'atr', 'log_ret']
        for c in expected:
            assert c in df.columns, f"Missing {c}"
            
        # Check no leaks (length should remain same minus dropna)
        # We dropna at end of generate_features
        assert len(df) < len(sample_ohlcv)
        assert len(df) > 0

    def test_rsi_bounds(self, sample_ohlcv):
        eng = FeatureEngineer()
        df = eng.generate_features(sample_ohlcv)
        assert df['rsi'].min() >= 0
        assert df['rsi'].max() <= 100

    def test_label_generation(self, sample_ohlcv):
        eng = FeatureEngineer()
        df = eng.generate_features(sample_ohlcv)
        
        # Generate Labels
        labeled = eng.generate_labels(df)
        
        # Check target column
        assert 'target' in labeled.columns
        assert 'z_score' in labeled.columns
        
        # Check values are 0-4
        unique_targets = labeled['target'].unique()
        for t in unique_targets:
            assert t in [0, 1, 2, 3, 4]
            
        # Check z-score logic validity
        # If z_score is huge (>1.5), target should be 4
        high_z = labeled[labeled['z_score'] > 1.6]
        if not high_z.empty:
            assert (high_z['target'] == 4).all()

class TestHistoryLoader:
    @patch('backend.ml.dataset.yf.download')
    def test_fetch_ticker_history_success(self, mock_download):
        # Mock yfinance response
        dates = pd.date_range(start='2020-01-01', periods=600)
        mock_df = pd.DataFrame({
            'Open': [100]*600,
            'High': [101]*600,
            'Low': [99]*600,
            'Close': np.random.normal(100, 1, 600), # Random values to avoid frozen check
            'Volume': [1000]*600
        }, index=dates)
        
        mock_download.return_value = mock_df
        
        loader = HistoryLoader()
        df, status = loader.fetch_ticker_history("TEST")
        
        assert status == "OK"
        assert df is not None
        assert 'close' in df.columns # Should be standardized lowercase
        assert len(df) == 600

    @patch('backend.ml.dataset.yf.download')
    def test_fetch_ticker_history_short(self, mock_download):
        # returns not enough data
        dates = pd.date_range(start='2024-01-01', periods=100)
        mock_df = pd.DataFrame({'Close': [100]*100}, index=dates)
        mock_download.return_value = mock_df
        
        loader = HistoryLoader()
        df, status = loader.fetch_ticker_history("SHORT")
        
        assert df is None
        assert "Insufficient History" in status

    @patch('backend.ml.dataset.yf.download')
    def test_fetch_ticker_history_multiindex_edge_case(self, mock_download):
        """
        Simulate yfinance returning MultiIndex columns [(Adj Close, AAPL), (Close, AAPL)...]
        This caused 'truth value of Series is ambiguous' errors before fixing.
        """
        dates = pd.date_range(start='2020-01-01', periods=600)
        
        # Create MultiIndex DataFrame
        # Levels: [Attribute, Ticker]
        columns = pd.MultiIndex.from_product([['Open', 'High', 'Low', 'Close', 'Volume'], ['AAPL']], names=['Price', 'Ticker'])
        
        data = np.random.normal(100, 1, size=(600, 5))
        mock_df = pd.DataFrame(data, index=dates, columns=columns)
        
        mock_download.return_value = mock_df
        
        loader = HistoryLoader()
        df, status = loader.fetch_ticker_history("AAPL")
        
        assert status == "OK"
        assert df is not None
        # Verify columns were flattened correctly
        expected_cols = ['open', 'high', 'low', 'close', 'volume']
        for c in expected_cols:
            assert c in df.columns
            
    @patch('backend.ml.dataset.yf.download')
    def test_fetch_history_frozen_multiindex(self, mock_download):
        """
        Test Frozen Price check when input is MultiIndex (which forces df['Close'] to be a DataFrame/Series ambiguous state).
        """
        dates = pd.date_range(start='2020-01-01', periods=600)
        columns = pd.MultiIndex.from_product([['Close'], ['AMZN']], names=['Price', 'Ticker'])
        
        # Create frozen data (last 5 values identical)
        vals = np.concatenate([np.random.normal(100, 1, 595), np.array([100.0, 100.0, 100.0, 100.0, 100.0])])
        mock_df = pd.DataFrame(vals, index=dates, columns=columns)
        
        # We need other columns too mostly so it doesn't crash before frozen check?
        # Actually Fetcher only checks 'Close' for frozen.
        # But standardization loops over columns.
        
        mock_download.return_value = mock_df
        
        loader = HistoryLoader()
        df, status = loader.fetch_ticker_history("AMZN")
        
        assert df is None
        assert "Frozen Price" in status

    @patch('backend.ml.dataset.yf.download')
    def test_fetch_history_ambiguous_nan_check(self, mock_download):
        """
        Test NaN check with MultiIndex (duplicate columns can cause Series ambiguity on isnull()).
        """
        dates = pd.date_range(start='2020-01-01', periods=600)
        # Create columns that might duplicate or be weird
        # We want exactly 2 columns to match the data shape (600, 2)
        columns = pd.MultiIndex.from_tuples([('Close', 'AMZN'), ('Close', 'AMZN')], names=['Attribute', 'Ticker'])
        
        # 600 rows, 2 columns.
        mock_df = pd.DataFrame(np.random.randn(600, 2), index=dates, columns=columns)
        
        # Let's inject MASSIVE NaNs (more than valid buffer)
        mock_df.iloc[200:300, :] = np.nan
        
        mock_download.return_value = mock_df
        
        loader = HistoryLoader()
        df, status = loader.fetch_ticker_history("AMZN")
        
        assert df is None
        assert "Too many NaNs" in status
        
    @patch('backend.ml.dataset.yf.download')
    def test_fetch_history_duplicate_columns(self, mock_download):
        """
        Test that duplicate columns (e.g. Close, Close) are deduplicated.
        """
        dates = pd.date_range(start='2020-01-01', periods=600)
        # Create duplicate columns in simple flat index
        columns = ['Open', 'High', 'Low', 'Close', 'Close', 'Volume']
        data = np.random.normal(100, 1, size=(600, 6))
        mock_df = pd.DataFrame(data, index=dates, columns=columns)
        mock_df.index.name = "Date"
        
        mock_download.return_value = mock_df
        
        loader = HistoryLoader()
        df, status = loader.fetch_ticker_history("DUPE")
        
        assert status == "OK"
        assert df is not None
        # reset_index adds 'index' if original index has no name. 
        # In real yfinance, index is named 'Date'. 
        # Let's adjust mock to mimic reality better
        
        # Now output should be 'date' (lowercase of Date)
        expected = ['date', 'open', 'high', 'low', 'close', 'volume']
        assert list(df.columns) == expected
