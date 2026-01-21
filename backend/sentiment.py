import os
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import json

from sqlalchemy.orm import Session
from models import StockSentiment
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch

# Configure Logging
logger = logging.getLogger(__name__)

# Constants
TIINGO_NEWS_URL = "https://api.tiingo.com/tiingo/news"
MODEL_NAME = "mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis"
BATCH_SIZE_NEWS = 50  # Tickers per API call
BATCH_SIZE_ML = 32    # Headlines per inference batch
CACHE_DURATION_HOURS = 24

class TiingoNewsFetcher:
    def __init__(self, api_key: str):
        self.api_key = api_key
        if not self.api_key:
            logger.warning("TIINGO_API_KEY is not set. Sentiment analysis will fail.")

    async def fetch_news_batch(self, session: aiohttp.ClientSession, tickers: List[str]) -> List[Dict]:
        """
        Fetch news for a list of tickers.
        """
        if not tickers:
            return []

        # Tiingo allows comma-separated tickers.
        ticker_str = ",".join(tickers)
        
        # 7-day window strictly
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        params = {
            'tickers': ticker_str,
            'token': self.api_key,
            'startDate': start_date,
            'limit': 1000, # Max limit per call
            'sortBy': 'publishedDate',
            'lang': 'en'
        }

        try:
            async with session.get(TIINGO_NEWS_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                elif response.status == 429:
                    logger.warning("Tiingo Rate Limit Hit!")
                    return []
                else:
                    logger.error(f"Tiingo API Error {response.status}: {await response.text()}")
                    return []
        except Exception as e:
            logger.error(f"Failed to fetch news for {tickers}: {e}")
            return []

class SentimentAnalyzer:
    def __init__(self):
        self.device = 0 if torch.cuda.is_available() else -1
        logger.info(f"Loading Sentiment Model... (Device: {'GPU' if self.device == 0 else 'CPU'})")
        
        # Helper to load pipeline only once
        self._pipeline = pipeline(
            "text-classification", 
            model=MODEL_NAME, 
            tokenizer=MODEL_NAME,
            device=self.device,
            truncation=True,
            max_length=512
        )

    def analyze_batch(self, texts: List[str]) -> List[float]:
        """
        Returns a list of scores between -1.0 (Negative) and 1.0 (Positive).
        """
        if not texts:
            return []

        # The model outputs labels: "negative", "neutral", "positive"
        results = self._pipeline(texts, batch_size=BATCH_SIZE_ML)
        
        scores = []
        for res in results:
            label = res['label'].lower()
            score = res['score']
            
            if label == 'negative':
                val = -score
            elif label == 'positive':
                val = score
            else: # neutral
                val = 0.0
            
            scores.append(val)
            
        return scores

class SentimentService:
    def __init__(self, db: Session):
        self.db = db
        self.api_key = os.getenv("TIINGO_API_KEY")
        self.fetcher = TiingoNewsFetcher(self.api_key)
        # Lazy load analyzer to save startup time if not needed immediately? 
        # For ingest script, we want it immediately.
        self.analyzer = SentimentAnalyzer()

    async def update_sentiments(self, tickers: List[str], force_refresh: bool = False):
        """
        Main orchestration method.
        Updates DB with fresh sentiment scores for the given tickers.
        """
        # 1. Filter out tickers that are already fresh
        tickers_to_process = []
        now = datetime.now(timezone.utc)
        cache_limit = now - timedelta(hours=CACHE_DURATION_HOURS)

        if force_refresh:
            tickers_to_process = tickers
        else:
            # Check DB
            # We can do a bulk query or just iterate. For 1500 stocks, bulk query is better.
            # But for simplicity in this rapid proto, let's query all existing stats.
            existing = self.db.query(StockSentiment).filter(StockSentiment.symbol.in_(tickers)).all()
            existing_map = {e.symbol: e.last_updated for e in existing}

            for t in tickers:
                last_upd = existing_map.get(t)
                # If never updated (None) or older than limit
                if not last_upd or last_upd.replace(tzinfo=timezone.utc) < cache_limit:
                    tickers_to_process.append(t)

        if not tickers_to_process:
            logger.info("All sentiments are fresh. Skipping update.")
            return

        logger.info(f"Updating sentiment for {len(tickers_to_process)} tickers...")

        # 2. Fetch News (Async Batching)
        # We chunk tickers into groups of 50 to respect URL limits / complexity
        ticker_chunks = [tickers_to_process[i:i + BATCH_SIZE_NEWS] for i in range(0, len(tickers_to_process), BATCH_SIZE_NEWS)]
        
        all_articles = []
        
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetcher.fetch_news_batch(session, chunk) for chunk in ticker_chunks]
            results = await asyncio.gather(*tasks)
            
            for res in results:
                all_articles.extend(res)

        # 3. Group Articles by Ticker
        # Tiingo returns a flat list of articles. Each has 'tickers' field (list of strings).
        # Note: One article can belong to multiple tickers.
        ticker_articles_map = {t: [] for t in tickers_to_process}
        
        for article in all_articles:
            # We enforce 7-day window again here just in case API returns stale, 
            # though 'startDate' param should handle it.
            tags = article.get('tickers', [])
            for tag in tags:
                tag_upper = tag.upper()
                if tag_upper in ticker_articles_map:
                    ticker_articles_map[tag_upper].append(article)

        # 4. Analyze and Upsert
        for symbol, articles in ticker_articles_map.items():
            if not articles:
                # No news -> Neural Score 0? Or None?
                # Let's write 0.0 but article_count = 0
                self._upsert_single(symbol, 0.0, 0, [])
                continue
            
            headlines = [a.get('title', '') for a in articles if a.get('title')]
            # Analyze
            scores = self.analyzer.analyze_batch(headlines)
            
            if not scores:
                avg_score = 0.0
            else:
                avg_score = sum(scores) / len(scores)

            # Prepare source data (audit trail)
            source_data = [
                {
                    'title': a.get('title'),
                    'url': a.get('url'),
                    'publishedDate': a.get('publishedDate')
                }
                for a in articles
            ]

            self._upsert_single(symbol, avg_score, len(articles), source_data)
            
        self.db.commit()
        logger.info(f"Sentiment update complete for {len(tickers_to_process)} tickers.")

    def _upsert_single(self, symbol, score, count, source_data):
        """Helper to update or insert row."""
        # Check existence
        row = self.db.query(StockSentiment).filter(StockSentiment.symbol == symbol).first()
        if not row:
            row = StockSentiment(symbol=symbol)
            self.db.add(row)
        
        row.score = score
        row.article_count = count
        row.sentiment_source_data = source_data
        row.last_updated = func.now()

from sqlalchemy.sql import func
