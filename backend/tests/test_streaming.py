import pytest
from unittest.mock import MagicMock, patch
from screener import Screener

@pytest.fixture
def mock_data_provider():
    return MagicMock()

@pytest.fixture
def screener(mock_data_provider):
    return Screener(mock_data_provider)

def test_screen_stocks_generator_yields_results(screener, mock_data_provider):
    # Setup
    tickers = ["AAPL", "GOOGL"]
    
    # Mock details
    mock_details_aapl = {
        "symbol": "AAPL", 
        "market_cap": 2000000000, 
        "free_cash_flow": 100000000,
        "peg_ratio": 1.5,
        "return_on_equity": 0.25,
        "operating_margins": 0.25,
        "debt_to_equity": 0.5,
        "current_price": 150,
        "target_mean": 180,
    }
    
    mock_details_googl = {
        "symbol": "GOOGL", 
        "market_cap": 2500000000, 
        "free_cash_flow": 80000000,
        "peg_ratio": 1.2,
        "return_on_equity": 0.20,
        "operating_margins": 0.20,
        "debt_to_equity": 0.1,
        "current_price": 2500,
        "target_mean": 3000,
    }

    # Configure mock to return different values based on input
    def get_details_side_effect(ticker):
        if ticker == "AAPL":
            return mock_details_aapl.copy()
        elif ticker == "GOOGL":
            return mock_details_googl.copy()
        return {}

    mock_data_provider.get_ticker_details.side_effect = get_details_side_effect
    mock_data_provider.get_advanced_metrics.return_value = {}

    # Execute
    results = list(screener.screen_stocks_generator(tickers))

    # Verify
    assert len(results) == 2
    symbols = [r["symbol"] for r in results]
    assert "AAPL" in symbols
    assert "GOOGL" in symbols
    
    # Check if metrics were calculated
    for res in results:
        assert "calculated_metrics" in res
        assert "score" in res["calculated_metrics"]

def test_screen_stocks_generator_handles_errors_gracefully(screener, mock_data_provider):
    tickers = ["AAPL", "BAD_TICKER"]
    
    mock_details_aapl = {
        "symbol": "AAPL", 
        "market_cap": 2000000000, 
        "free_cash_flow": 100000000
    }

    def get_details_side_effect(ticker):
        if ticker == "AAPL":
            return mock_details_aapl.copy()
        elif ticker == "BAD_TICKER":
            raise Exception("API Error")
        return {}

    mock_data_provider.get_ticker_details.side_effect = get_details_side_effect
    mock_data_provider.get_advanced_metrics.return_value = {}

    # Execute
    results = list(screener.screen_stocks_generator(tickers))

    # Verify - Should only get AAPL result, BAD_TICKER should be skipped (printed to stderr)
    assert len(results) == 1
    assert results[0]["symbol"] == "AAPL"
