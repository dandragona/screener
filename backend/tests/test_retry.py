import pytest
import time
from unittest.mock import Mock, patch
from utils import retry_with_backoff

class TestRetry:
    def test_success_no_retry(self):
        """Test that functionality works without retry if no error occurs."""
        mock_func = Mock(return_value="success")
        
        decorated = retry_with_backoff(retries=3)(mock_func)
        result = decorated()
        
        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_on_failure(self):
        """Test that it retries specified number of times."""
        # Use a side_effect that raises exception twice then succeeds
        mock_func = Mock(side_effect=[ValueError("fail 1"), ValueError("fail 2"), "success"])
        mock_func.__name__ = "mock_func"
        
        # set backoff to essentially 0 for speed
        decorated = retry_with_backoff(retries=3, backoff_in_seconds=0.01)(mock_func)
        result = decorated()
        
        assert result == "success"
        assert mock_func.call_count == 3

    def test_max_retries_exceeded(self):
        """Test that it raises exception after max retries."""
        mock_func = Mock(side_effect=ValueError("persistent fail"))
        mock_func.__name__ = "mock_func"
        
        decorated = retry_with_backoff(retries=2, backoff_in_seconds=0.01)(mock_func)
        
        with pytest.raises(ValueError, match="persistent fail"):
            decorated()
            
        # call_count should be retries + 1 (initial try + 2 retries)
        # Wait, the logic is:
        # x starts at 0.
        # Try -> fail.
        # if x == retries: raise.
        # ...
        # x += 1.
        # So:
        # 1. x=0. Call. Fail. x!=2. x=1.
        # 2. x=1. Call. Fail. x!=2. x=2.
        # 3. x=2. Call. Fail. x==2 -> Raise.
        # Total calls = 3.
        assert mock_func.call_count == 3
