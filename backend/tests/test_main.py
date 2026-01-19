from fastapi.testclient import TestClient
from main import app
from unittest.mock import patch

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@patch("main.screener.screen_stocks_generator")
def test_screen_stocks_endpoint(mock_screen_gen):
    # Mock return value (generator)
    def mock_gen(tickers):
        yield {"symbol": "TEST", "score": 3}
    mock_screen_gen.side_effect = mock_gen
    
    response = client.get("/screen?tickers=TEST")
    assert response.status_code == 200
    
    # Parse NDJSON
    import json
    lines = response.text.strip().split('\n')
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data == {"symbol": "TEST", "score": 3}
    
    mock_screen_gen.assert_called_with(["TEST"])

@patch("main.data_provider.get_ticker_details")
def test_get_ticker_details(mock_get_details):
    mock_get_details.return_value = {"symbol": "AAPL", "price": 150}
    
    response = client.get("/ticker/AAPL")
    assert response.status_code == 200
    assert response.json() == {"symbol": "AAPL", "price": 150}

@patch("main.data_provider.get_ticker_details")
def test_get_ticker_details_not_found(mock_get_details):
    mock_get_details.side_effect = Exception("Ticker not found")
    
    response = client.get("/ticker/INVALID")
    assert response.status_code == 404

@patch("main.ai_generator.generate_description")
@patch("main.data_provider.get_ticker_details")
def test_analyze_stock_endpoint(mock_get_details, mock_generate_desc):
    # Mock details
    mock_get_details.return_value = {
        "symbol": "AAPL", 
        "price": 150, 
        "free_cash_flow": 1000, 
        "market_cap": 20000
    }
    # Mock AI response
    mock_generate_desc.return_value = "AI Analysis Result"
    
    response = client.get("/analyze/AAPL")
    
    assert response.status_code == 200
    assert response.json() == {
        "symbol": "AAPL",
        "analysis": "AI Analysis Result"
    }
    
    mock_get_details.assert_called_with("AAPL")
    mock_generate_desc.assert_called()
