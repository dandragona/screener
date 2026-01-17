import pytest
from unittest.mock import MagicMock
from screener import Screener
from data_provider import DataProvider

class TestScreener:
    @pytest.fixture
    def mock_provider(self):
        provider = MagicMock(spec=DataProvider)
        return provider

    def test_screen_stocks_filter_market_cap(self, mock_provider):
        screener = Screener(mock_provider)
        
        # Mock returns small cap
        mock_provider.get_ticker_details.return_value = {
            "symbol": "SMALL",
            "market_cap": 1_000_000,
            "free_cash_flow": 1, 
            "return_on_equity": 0.2
        }
        
        results = screener.screen_stocks(["SMALL"])
        assert len(results) == 0

    def test_screen_stocks_valid_pass(self, mock_provider):
        screener = Screener(mock_provider)
        
        # Mock returns good company
        mock_provider.get_ticker_details.return_value = {
            "symbol": "GOOD",
            "market_cap": 10_000_000_000,
            "free_cash_flow": 1_000_000_000, # P/FCF = 10 (Score +15)
            "peg_ratio": 1.0,               # PEG <= 1.0 (Score +15)
            "return_on_equity": 0.2,        # ROE >= 20% (Score +15)
            "operating_margins": 0.2,       # Margins >= 20% (Score +10)
            "debt_to_equity": 0.5,          # D/E <= 0.5 (Score +10)
            "current_price": 100,
            "target_mean": 120              # Upside 20% (Score +15)
        }
        # Total fundamental score = 15+15+15+10+10+15 = 80
        
        # Mock advanced metrics
        mock_provider.get_advanced_metrics.return_value = {
            "iv_short": 0.3,
            "historical_volatility": 0.4,   # IV < HV (+5)
            "iv_term_structure_ratio": 1.05,# Ratio < 1.1 (+5)
            "insider_net_shares": 1000      # Net > 0 (+10)
        }
        
        results = screener.screen_stocks(["GOOD"])
        assert len(results) == 1
        assert results[0]["symbol"] == "GOOD"
        # Total score should be 80 (fund) + 20 (adv) = 100
        assert results[0]["calculated_metrics"]["score"] == 100.0

    def test_screen_stocks_error_handling(self, mock_provider):
        screener = Screener(mock_provider)
        
        # Mock raises exception for one, works for another
        mock_provider.get_ticker_details.side_effect = [
            Exception("API Error"),
            {
                "symbol": "OK",
                "market_cap": 5_000_000_000,
                "free_cash_flow": 500_000_000,
                "return_on_equity": 0.2
            }
        ]
        mock_provider.get_advanced_metrics.return_value = {}
        
        results = screener.screen_stocks(["BAD", "OK"])
        assert len(results) == 1
        assert results[0]["symbol"] == "OK"

    def test_screen_stocks_infinite_values(self, mock_provider):
        screener = Screener(mock_provider)
        
        mock_provider.get_ticker_details.return_value = {
            "symbol": "INF",
            "market_cap": 3_000_000_000,
            "free_cash_flow": 0, # Causes division by zero/inf P/FCF
            "peg_ratio": float('inf'),
            "return_on_equity": 0.1
        }
        mock_provider.get_advanced_metrics.return_value = {}
        
        results = screener.screen_stocks(["INF"])
        assert len(results) == 1
        # P/FCF should be sanitized to None
        assert results[0]["calculated_metrics"]["p_fcf"] is None

    def test_screen_stocks_price_targets(self, mock_provider):
        screener = Screener(mock_provider)
        
        mock_provider.get_ticker_details.return_value = {
            "symbol": "TGT",
            "market_cap": 5_000_000_000,
            "free_cash_flow": 100_000_000,
            "target_mean": 150.0,
            "target_high": float('inf'), # Should be sanitized
            "target_low": None,          # Should handle None
            "return_on_equity": 0.2
        }
        mock_provider.get_advanced_metrics.return_value = {}
        
        results = screener.screen_stocks(["TGT"])
        assert len(results) == 1
        assert results[0]["target_mean"] == 150.0
        assert results[0]["target_high"] is None # Sanitized
        assert results[0]["target_low"] is None

    def test_screen_stocks_negative_fcf(self, mock_provider):
        screener = Screener(mock_provider)
        
        mock_provider.get_ticker_details.return_value = {
            "symbol": "NEG_FCF",
            "market_cap": 2_000_000_000,
            "free_cash_flow": -100_000_000, # Negative FCF
            "return_on_equity": 0.1
        }
        mock_provider.get_advanced_metrics.return_value = {}
        
        results = screener.screen_stocks(["NEG_FCF"])
        assert len(results) == 1
        # P/FCF should be negative float
        p_fcf = results[0]["calculated_metrics"]["p_fcf"]
        assert p_fcf == -20.0
        # Score should be > 0 because of ROE
        assert results[0]["calculated_metrics"]["score"] > 0

    def test_advanced_metrics_contribution(self, mock_provider):
        """Verify that individual advanced metrics contribute the correct points."""
        screener = Screener(mock_provider)
        
        def get_base_details():
            return {
                "symbol": "ADV",
                "market_cap": 10_000_000_000,
                "free_cash_flow": None,
                "return_on_equity": 0 # 0 pts
            }
        
        # Case 1: IV < HV only (+5 pts)
        mock_provider.get_ticker_details.return_value = get_base_details()
        mock_provider.get_advanced_metrics.return_value = {
            "iv_short": 0.2,
            "historical_volatility": 0.3,
            "iv_term_structure_ratio": 1.5, # > 1.1 (0 pts)
            "insider_net_shares": 0         # 0 pts
        }
        results = screener.screen_stocks(["ADV"])
        assert results[0]["calculated_metrics"]["score"] == 5.0
        
        # Case 2: Term Structure < 1.1 only (+5 pts)
        mock_provider.get_ticker_details.return_value = get_base_details()
        mock_provider.get_advanced_metrics.return_value = {
            "iv_short": 0.3,
            "historical_volatility": 0.2, # IV > HV (0 pts)
            "iv_term_structure_ratio": 1.05,
            "insider_net_shares": -100     # < 0 (0 pts)
        }
        results = screener.screen_stocks(["ADV"])
        assert results[0]["calculated_metrics"]["score"] == 5.0

        # Case 3: Insider Buying only (+10 pts)
        mock_provider.get_ticker_details.return_value = get_base_details()
        mock_provider.get_advanced_metrics.return_value = {
            "insider_net_shares": 5000,
            "iv_short": None,
            "historical_volatility": None,
            "iv_term_structure_ratio": None
        }
        results = screener.screen_stocks(["ADV"])
        assert results[0]["calculated_metrics"]["score"] == 10.0

        # Case 4: All Advanced Triggered (+20 pts)
        mock_provider.get_ticker_details.return_value = get_base_details()
        mock_provider.get_advanced_metrics.return_value = {
            "iv_short": 0.2,
            "historical_volatility": 0.3,
            "iv_term_structure_ratio": 1.0,
            "insider_net_shares": 1
        }
        results = screener.screen_stocks(["ADV"])
        assert results[0]["calculated_metrics"]["score"] == 20.0
