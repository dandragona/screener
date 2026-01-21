
import pytest
import pandas as pd
import numpy as np
import os
import sys

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.features import FeatureEngineer
from ml.backfill_iv import process_file
from unittest.mock import MagicMock

def test_lagged_returns():
    fe = FeatureEngineer()
    df = pd.DataFrame({
        'close': [100, 101, 102, 101, 103, 105, 106, 107, 108, 109, 110, 111, 112],
        'volume': [1000]*13,
    })
    
    # We need enough data for 10d lag + 30d vol? 
    # generate_features drops NaNs. 
    # rolling(30) will result in NaNs for first 29 rows.
    # So we need at least 31 rows.
    
    dates = pd.date_range(start='2024-01-01', periods=50)
    df = pd.DataFrame({
        'date': dates,
        'close': np.linspace(100, 150, 50),
        'volume': [1000]*50,
        'high': np.linspace(101, 151, 50),
        'low': np.linspace(99, 149, 50),
    })
    
    features = fe.generate_features(df)
    
    assert 'log_ret_1d' in features.columns
    assert 'log_ret_3d' in features.columns
    assert 'log_ret_5d' in features.columns
    assert 'log_ret_10d' in features.columns
    
    # Check logic
    # log_ret = ln(Pt / Pt-1)
    # log_ret_1d = shift(1) of log_ret
    # So index i has log_ret of i. log_ret_1d of i is log_ret of i-1.
    
    assert not features['log_ret_1d'].isnull().any()

def test_sector_encoding():
    fe = FeatureEngineer()
    dates = pd.date_range(start='2024-01-01', periods=300)
    df = pd.DataFrame({
        'date': dates,
        'close': np.linspace(100, 150, 300),
        'high': np.linspace(101, 151, 300),
        'low': np.linspace(99, 149, 300),
        'volume': [1000]*300,
        'sector': ['Information Technology'] * 300
    })
    
    features = fe.generate_features(df)
    
    assert 'sector_information_technology' in features.columns
    # Should be 1
    assert features['sector_information_technology'].iloc[0] == 1
    # Check another sector is 0
    assert 'sector_energy' in features.columns
    assert features['sector_energy'].iloc[0] == 0

def test_process_file_backfill_iv(tmp_path):
    # Mock Provider
    mock_provider = MagicMock()
    mock_provider.get_iv_history.return_value = [
        {'date': pd.Timestamp('2024-01-02'), 'iv30': 0.25},
        {'date': pd.Timestamp('2024-01-03'), 'iv30': 0.26}
    ]
    
    # Create Dummy Parquet with enough rows > 100
    dates = pd.date_range(start='2024-01-01', periods=150)
    df = pd.DataFrame({
        'date': dates,
        'close': np.linspace(100, 200, 150),
        'volume': [1000]*150
    })
    
    file_path = tmp_path / "TEST.parquet"
    df.to_parquet(file_path)
    
    # Run Process
    res = process_file(str(file_path), mock_provider)
    
    assert "Updated TEST" in res
    
    # Load and check
    updated_df = pd.read_parquet(file_path)
    assert 'iv30' in updated_df.columns
    
    # Check merge - 2024-01-02 should have 0.25
    row = updated_df[updated_df['date'] == '2024-01-02']
    assert not row.empty
    assert row.iloc[0]['iv30'] == 0.25
