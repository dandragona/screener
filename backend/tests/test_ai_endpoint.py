
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import pytest
from datetime import date
from sqlalchemy.orm import Session

# Import app and models
from main import app, get_db
from models import ScreenResult

# Setup client
client = TestClient(app)

# Mock DB Session
@pytest.fixture
def mock_db():
    return MagicMock(spec=Session)

# Override get_db dependency
@pytest.fixture
def override_get_db(mock_db):
    def _get_db():
        yield mock_db
    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides = {}

@patch("main.ai_generator")
def test_analyze_stock_success(mock_ai_generator, mock_db, override_get_db):
    # Setup Mock Data
    symbol = "TEST"
    mock_result = MagicMock(spec=ScreenResult)
    mock_result.symbol = symbol
    mock_result.date = date.today()
    mock_result.raw_data = {
        "symbol": "TEST",
        "market_cap": 1000,
        "free_cash_flow": 100,
        "calculated_metrics": {"score": 80}
    }
    
    # Configure DB Query Mock
    # db.query(ScreenResult).filter(...).order_by(...).first()
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_order_by = mock_filter.order_by.return_value
    mock_order_by.first.return_value = mock_result
    
    # Configure AI Generator Mock
    mock_ai_generator.generate_description.return_value = "Buy this stock."
    
    # Make Request
    response = client.get(f"/analyze/{symbol}")
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == symbol
    assert data["analysis"] == "Buy this stock."
    
    # Verify DB was called
    mock_db.query.assert_called_with(ScreenResult)
    # Verify AI generator was called with correct data
    mock_ai_generator.generate_description.assert_called_once()
    args, _ = mock_ai_generator.generate_description.call_args
    assert args[0] == symbol
    assert args[1]["market_cap"] == 1000
    # check if p_fcf was calculated
    assert args[1]["calculated_metrics"]["p_fcf"] == 10.0

@patch("main.ai_generator")
def test_analyze_stock_not_found(mock_ai_generator, mock_db, override_get_db):
    # Configure DB to return None
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_order_by = mock_filter.order_by.return_value
    mock_order_by.first.return_value = None
    
    response = client.get("/analyze/UNKNOWN")
    
    assert response.status_code == 404
    assert "No screened data found" in response.json()["detail"]

@patch("main.ai_generator")
def test_analyze_stock_no_raw_data(mock_ai_generator, mock_db, override_get_db):
    # Setup Mock Data with missing raw_data
    mock_result = MagicMock(spec=ScreenResult)
    mock_result.symbol = "BAD"
    mock_result.raw_data = None
    
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_order_by = mock_filter.order_by.return_value
    mock_order_by.first.return_value = mock_result
    
    response = client.get("/analyze/BAD")
    
    assert response.status_code == 404
