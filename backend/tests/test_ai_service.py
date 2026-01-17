import pytest
from unittest.mock import MagicMock, patch
from ai_service import AIDescriptionGenerator

# Mock google.generativeai to avoid hitting real API
@pytest.fixture
def mock_genai():
    with patch("ai_service.genai") as mock:
        yield mock

@pytest.fixture
def mock_env():
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
        yield

def test_init_with_key(mock_env, mock_genai):
    service = AIDescriptionGenerator()
    mock_genai.configure.assert_called_with(api_key="fake_key")
    assert service.model is not None

def test_init_without_key():
    with patch.dict("os.environ", {}, clear=True):
        service = AIDescriptionGenerator()
        assert service.model is None

def test_generate_description_success(mock_env, mock_genai):
    service = AIDescriptionGenerator()
    
    # Mock model response
    mock_response = MagicMock()
    mock_response.text = "Buy this stock."
    service.model.generate_content.return_value = mock_response
    
    details = {
        "current_price": 100,
        "market_cap": 1000000,
        "trailing_pe": 15,
        "calculated_metrics": {"p_fcf": 10}
    }
    
    result = service.generate_description("TEST", details)
    assert result == "Buy this stock."
    service.model.generate_content.assert_called_once()
    
    # Check that prompt contains ticker
    args, _ = service.model.generate_content.call_args
    assert "TEST" in args[0]
    assert "100" in args[0]

def test_generate_description_no_key():
    with patch.dict("os.environ", {}, clear=True):
        service = AIDescriptionGenerator()
        result = service.generate_description("TEST", {})
        assert "AI analysis unavailable" in result
