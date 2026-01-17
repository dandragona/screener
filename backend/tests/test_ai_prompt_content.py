
import pytest
from unittest.mock import MagicMock, patch
from ai_service import AIDescriptionGenerator

@pytest.fixture
def mock_genai():
    with patch("ai_service.genai") as mock:
        yield mock

@pytest.fixture
def mock_env():
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
        yield

def test_prompt_content_includes_all_metrics(mock_env, mock_genai):
    service = AIDescriptionGenerator()
    
    # Mock model response
    mock_response = MagicMock()
    mock_response.text = "Analysis"
    service.model.generate_content.return_value = mock_response
    
    details = {
        "current_price": 150.50,
        "market_cap": 2000000000,
        "trailing_pe": 25.5,
        "forward_pe": 20.0,
        "peg_ratio": 1.2,
        "return_on_equity": 0.15,
        "operating_margins": 0.25,
        "debt_to_equity": 0.8,
        "calculated_metrics": {
            "p_fcf": 18.2,
            "score": 85
        },
        "target_mean": 170.0,
        "target_high": 200.0,
        "target_low": 140.0,
        "historical_volatility": 0.35,
        "iv_short": 0.30,
        "iv_long": 0.32,
        "insider_net_shares": 5000
    }
    
    service.generate_description("AAPL", details)
    
    args, _ = service.model.generate_content.call_args
    prompt = args[0]
    
    # Verify all metrics are in the prompt
    assert "AAPL" in prompt
    assert "150.5" in prompt
    assert "2000000000" in prompt
    assert "25.5" in prompt
    assert "20.0" in prompt
    assert "1.2" in prompt
    assert "18.2" in prompt
    assert "0.15" in prompt
    assert "0.25" in prompt # Operating Margins
    assert "0.8" in prompt
    
    # Analyst Estimates
    assert "170.0" in prompt
    assert "200.0" in prompt
    assert "140.0" in prompt
    
    # Volatility & Insider
    assert "0.35" in prompt
    assert "0.3" in prompt # iv_short might be stringified as 0.3
    assert "0.32" in prompt
    assert "5000" in prompt
    
    # Score
    assert "85" in prompt
