
import sys
import os
from sqlalchemy import create_engine, desc, asc
from sqlalchemy.orm import sessionmaker

# Setup DB connection path
# Add current directory and backend directory to sys.path
sys.path.append(os.getcwd())
backend_path = os.path.join(os.getcwd(), 'backend')
if backend_path not in sys.path:
    sys.path.append(backend_path)

try:
    from backend.database import engine, SessionLocal
    from backend.models import StockSentiment
except ImportError:
    # If running from inside backend/ or something else
    try:
        from database import engine, SessionLocal
        from models import StockSentiment
    except ImportError:
        print("Could not import backend modules. Make sure you are in the project root.")
        sys.exit(1)

def print_sentiment(label, sentiment):
    if not sentiment:
        print(f"\n--- {label}: None ---")
        return
    
    print(f"\n--- {label} ---")
    print(f"Symbol: {sentiment.symbol}")
    print(f"Score: {sentiment.score}")
    print(f"Article Count: {sentiment.article_count}")
    print("Headlines:")
    if sentiment.sentiment_source_data:
        # Limit to 5 headlines for brevity
        for i, article in enumerate(sentiment.sentiment_source_data):
             if i >= 5:
                 print(f" - ... and {len(sentiment.sentiment_source_data) - 5} more")
                 break
             print(f" - {article.get('title')} ({article.get('publishedDate')})")
    else:
        print(" No source data found.")

def main():
    db = SessionLocal()
    try:
        print("Connected to DB.")
        # 1. Low Score
        low = db.query(StockSentiment).filter(StockSentiment.article_count > 0).order_by(asc(StockSentiment.score)).first()
        print_sentiment("Lowest Sentiment", low)

        # 2. High Score
        high = db.query(StockSentiment).filter(StockSentiment.article_count > 0).order_by(desc(StockSentiment.score)).first()
        print_sentiment("Highest Sentiment", high)

        # 3. Neutral Score (closest to 0)
        neutral = db.query(StockSentiment).filter(
            StockSentiment.article_count > 0, 
            StockSentiment.score >= -0.1, 
            StockSentiment.score <= 0.1
        ).order_by(asc(StockSentiment.score)).first()
        
        print_sentiment("Neutral Sentiment", neutral)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
