import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sentiment import SentimentService, TiingoNewsFetcher, StockSentiment
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base
import asyncio
from datetime import datetime

# Setup in-memory DB for testing
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.mark.asyncio
async def test_sentiment_update_flow(db):
    """
    Test that update_sentiments fetches news, analyzes it, and saves it to DB.
    """
    # Mock Tickers
    tickers = ["AAPL", "GOOG"]

    # Mock Fetcher Response
    mock_news = [
        {"title": "Apple is doing great things", "publishedDate": "2023-10-01T12:00:00Z", "url": "http://a.com", "tickers": ["AAPL"]},
        {"title": "Google released a new bad product", "publishedDate": "2023-10-01T12:00:00Z", "url": "http://g.com", "tickers": ["GOOG"]}
    ]

    # Initialize Service
    service = SentimentService(db)
    
    # Patch the fetcher
    service.fetcher.fetch_news_batch = AsyncMock(return_value=mock_news)
    
    # Patch the analyzer to return deterministic scores
    # AAPL -> Positive (0.9), GOOG -> Negative (-0.9)
    service.analyzer.analyze_batch = MagicMock(side_effect=[[0.9], [-0.9]]) 
    
    # Run Update
    await service.update_sentiments(tickers, force_refresh=True)

    # Verify DB
    aapl_sent = db.query(StockSentiment).filter_by(symbol="AAPL").first()
    goog_sent = db.query(StockSentiment).filter_by(symbol="GOOG").first()

    assert aapl_sent is not None
    assert aapl_sent.score == 0.9
    assert aapl_sent.article_count == 1
    
    assert goog_sent is not None
    assert goog_sent.score == -0.9
    assert goog_sent.article_count == 1
    
    # Check source data JSON
    assert aapl_sent.sentiment_source_data[0]['title'] == "Apple is doing great things"

    print("Sentiment Update Test Passed!")
