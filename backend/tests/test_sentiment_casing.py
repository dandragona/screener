
import pytest
from unittest.mock import MagicMock, AsyncMock
from sentiment import SentimentService

@pytest.mark.asyncio
async def test_sentiment_casing_normalization():
    """
    Test that lowercase tickers from API are correctly matched to uppercase tickers in the system.
    """
    # Mock DB
    mock_db = MagicMock()
    
    # Mock Service
    service = SentimentService(mock_db)
    
    # Mock Fetcher
    service.fetcher.fetch_news_batch = AsyncMock(return_value=[
        {
            'title': 'Good news for Apple',
            'url': 'http://example.com/1',
            'publishedDate': '2025-04-01T10:00:00Z',
            'tickers': ['aapl', 'tech'] # LOWERCASE ticker from API
        },
        {
            'title': 'Tesla is moving',
            'url': 'http://example.com/2',
            'publishedDate': '2025-04-01T10:00:00Z',
            'tickers': ['tsla'] # LOWERCASE ticker from API
        }
    ])
    
    # Mock Analyzer (always return positive score)
    service.analyzer.analyze_batch = MagicMock(return_value=[0.9])
    
    # Mock Upsert
    service._upsert_single = MagicMock()
    
    # Execute
    tickers = ["AAPL", "TSLA"]
    await service.update_sentiments(tickers, force_refresh=True)
    
    # Verify _upsert_single was called for AAPL and TSLA
    # The keys in the internal map should be normalized to AAPL and TSLA
    
    # Check calls
    calls = service._upsert_single.call_args_list
    
    # We expect 2 calls
    assert len(calls) == 2
    
    symbols_processed = [c[0][0] for c in calls]
    assert "AAPL" in symbols_processed
    assert "TSLA" in symbols_processed
    
    # Verify that 'aapl' from API was matched to 'AAPL' from request
    # If normalization failed, the article would be ignored or mapped incorrectly if not careful
    # In our implementation, we iterate over tickers_to_process ('AAPL'), initialize map with 'AAPL',
    # and when processing API results, we uppercase tags. 'aapl' -> 'AAPL', matches key.
    
    # Ensure count is 1 for each
    for c in calls:
        sym, score, count, source = c[0]
        assert count == 1
        assert score == 0.9

