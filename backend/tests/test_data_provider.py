import pytest
from unittest.mock import MagicMock, patch
from data_provider import YFinanceProvider

class TestYFinanceProvider:
    @pytest.fixture
    def mock_yf_ticker(self):
        with patch("data_provider.yf.Ticker") as mock:
            yield mock

    def test_get_ticker_details_mapping(self, mock_yf_ticker):
        # Setup mock return values
        mock_instance = MagicMock()
        mock_yf_ticker.return_value = mock_instance
        
        mock_instance.info = {
            "symbol": "TEST",
            "currentPrice": 100.0,
            "marketCap": 1_000_000_000,
            "trailingPE": 15.5,
            "pegRatio": 1.2,
            "priceToBook": 2.5,
            "fiftyDayAverage": 95.0,
            "twoHundredDayAverage": 90.0,
            "beta": 1.1,
            "targetMeanPrice": 120.0,
            "targetHighPrice": 150.0,
            "targetLowPrice": 80.0,
            "trailingEps": 6.45,
            "forwardEps": 7.0,
            "debtToEquity": 50.0,
            "returnOnEquity": 0.15,
            "freeCashflow": 50_000_000,
            "operatingMargins": 0.25,
            "ebitda": 200_000_000,
            "totalRevenue": 800_000_000
        }

        provider = YFinanceProvider()
        details = provider.get_ticker_details("TEST")

        # Verify mapping
        assert details["symbol"] == "TEST"
        assert details["current_price"] == 100.0
        assert details["market_cap"] == 1_000_000_000
        assert details["pe_ratio"] == 15.5
        assert details["peg_ratio"] == 1.2
        assert details["price_to_book"] == 2.5
        assert details["fifty_day_average"] == 95.0
        assert details["target_mean"] == 120.0
        assert details["target_high"] == 150.0
        assert details["trailing_eps"] == 6.45
        assert details["return_on_equity"] == 0.15
        
        mock_yf_ticker.assert_called_with("TEST")

    def test_get_ticker_details_missing_fields(self, mock_yf_ticker):
        # Mock mostly empty info
        mock_instance = MagicMock()
        mock_yf_ticker.return_value = mock_instance
        mock_instance.info = {}

        provider = YFinanceProvider()
        details = provider.get_ticker_details("EMPTY")

        # Should handle missing keys gracefully (return None)
        assert details["current_price"] is None
        assert details["market_cap"] is None
        assert details["peg_ratio"] is None
        assert details["target_mean"] is None

    def test_get_ticker_details_peg_fallback(self, mock_yf_ticker):
        # Test fallback to trailingPegRatio if pegRatio is missing
        mock_instance = MagicMock()
        mock_yf_ticker.return_value = mock_instance
        mock_instance.info = {
            "pegRatio": None,
            "trailingPegRatio": 1.8
        }

        provider = YFinanceProvider()
        details = provider.get_ticker_details("PEG")

        assert details["peg_ratio"] == 1.8

    def test_get_options_chain(self, mock_yf_ticker):
        mock_instance = MagicMock()
        mock_yf_ticker.return_value = mock_instance
        mock_instance.options = ("2023-01-01", "2023-02-01")

        provider = YFinanceProvider()
        chain = provider.get_options_chain("OPT")

        assert chain["symbol"] == "OPT"
        assert chain["expirations"] == ("2023-01-01", "2023-02-01")
        mock_yf_ticker.assert_called_with("OPT")
