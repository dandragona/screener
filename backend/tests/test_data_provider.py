import pytest
from unittest.mock import MagicMock, patch, call
from data_provider import YFinanceProvider, PolygonProvider

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

class TestPolygonProvider:
    @patch("data_provider.PolygonProvider._get_json")
    def test_get_all_contracts_expired_logic(self, mock_get_json):
        # Verify that we fetch BOTH expired and active contracts
        provider = PolygonProvider()
        symbol = "TEST"
        
        # Mock responses
        # Call 1: Expired loop (returns 1 contract, no next_url)
        # Call 2: Active loop (returns 1 contract, no next_url)
        mock_get_json.side_effect = [
            {"results": [{"ticker": "EXP"}], "next_url": None}, 
            {"results": [{"ticker": "ACT"}], "next_url": None}
        ]
        
        contracts = provider._get_all_contracts(symbol)
        
        assert len(contracts) == 2
        assert contracts[0]["ticker"] == "EXP"
        assert contracts[1]["ticker"] == "ACT"
        
        # Verify calls
        assert mock_get_json.call_count == 2
        
        # Check first call had expired=true
        call1_kwargs = mock_get_json.call_args_list[0][0][1] # params
        assert call1_kwargs.get("expired") == "true"
        
        # Check second call had expired=false
        call2_kwargs = mock_get_json.call_args_list[1][0][1] # params
        assert call2_kwargs.get("expired") == "false"

    @patch("data_provider.PolygonProvider._get_all_contracts")
    def test_get_iv_history_optimization(self, mock_get_all_contracts):
        # verify that get_iv_history calculates correct bounds and passes them to _get_all_contracts
        import pandas as pd
        provider = PolygonProvider()
        symbol = "OPT"
        
        # 1. Create Mock History
        # Low = 100, High = 200
        data = {
            "Close": [100.0, 150.0, 200.0]
        }
        df = pd.DataFrame(data, index=["2023-01-01", "2023-01-02", "2023-01-03"])
        
        # Mock _get_all_contracts to return empty so we don't crash later logic
        mock_get_all_contracts.return_value = []
        
        # 2. Call method
        provider.get_iv_history(symbol, df)
        
        # 3. Verify arguments
        # Expected Min = 100 * 0.5 = 50.0
        # Expected Max = 200 * 1.5 = 300.0
        
        mock_get_all_contracts.assert_called_once()
        _, kwargs = mock_get_all_contracts.call_args
        
        assert kwargs["min_strike"] == 50.0
        assert kwargs["max_strike"] == 300.0
