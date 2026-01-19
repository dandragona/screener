import unittest
from unittest.mock import MagicMock, patch
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Base, Stock, ScreenResult
from ingest import upsert_stock, upsert_result, upsert_history, calculate_and_save_rank
from datetime import date, timedelta

class TestIngestion(unittest.TestCase):
    def setUp(self):
        # In-memory SQLite for testing
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.db = Session()

    def tearDown(self):
        self.db.close()

    def test_upsert_stock(self):
        data = {
            "symbol": "TEST",
            "shortName": "Test Corp",
            "sector": "Technology",
            "industry": "Software"
        }
        
        # 1. Insert
        upsert_stock(self.db, data)
        self.db.commit()
        
        stock = self.db.query(Stock).filter_by(symbol="TEST").first()
        self.assertIsNotNone(stock)
        self.assertEqual(stock.company_name, "Test Corp")
        
        # 2. Update
        data["shortName"] = "Test Corp Updated"
        upsert_stock(self.db, data)
        self.db.commit()
        
        stock = self.db.query(Stock).filter_by(symbol="TEST").first()
        self.assertEqual(stock.company_name, "Test Corp Updated")

    def test_upsert_result(self):
        data = {
            "symbol": "TEST",
            "calculated_metrics": {
                "score": 85.5,
                "p_fcf": 12.5
            },
            "market_cap": 1000000,
            "peg_ratio": 1.2
        }
        
        # Need stock first due to ForeignKey
        upsert_stock(self.db, {"symbol": "TEST"})
        self.db.commit()
        
        # 1. Insert Result
        upsert_result(self.db, data)
        self.db.commit()
        
        res = self.db.query(ScreenResult).filter_by(symbol="TEST").first()
        self.assertIsNotNone(res)
        self.assertEqual(res.score, 85.5)
        self.assertEqual(res.p_fcf, 12.5)
        
        # 2. Update Result (Same Day)
        data["calculated_metrics"]["score"] = 90.0
        upsert_result(self.db, data)
        self.db.commit()
        
        results = self.db.query(ScreenResult).filter_by(symbol="TEST").all()
        self.assertEqual(len(results), 1) # Should still be 1 record for today
        self.assertEqual(results[0].score, 90.0)

    def test_upsert_history(self):
        # 1. Setup
        upsert_stock(self.db, {"symbol": "HIST"})
        self.db.commit()
        
        history = [
            {"date": date(2023, 1, 1), "iv30": 0.20},
            {"date": date(2023, 1, 2), "iv30": 0.25}
        ]
        
        # 2. Upsert
        upsert_history(self.db, "HIST", history)
        
        # 3. Verify
        res1 = self.db.query(ScreenResult).filter_by(symbol="HIST", date=date(2023, 1, 1)).first()
        self.assertIsNotNone(res1)
        self.assertEqual(res1.iv30, 0.20)
        
        res2 = self.db.query(ScreenResult).filter_by(symbol="HIST", date=date(2023, 1, 2)).first()
        self.assertIsNotNone(res2)
        self.assertEqual(res2.iv30, 0.25)
        
    def test_calculate_and_save_rank(self):
        symbol = "RANK"
        upsert_stock(self.db, {"symbol": symbol})
        self.db.commit()
        
        # 1. Seed History (Min=0.20, Max=0.80)
        history = [
            {"date": date.today() - timedelta(days=100), "iv30": 0.20}, # Low
            {"date": date.today() - timedelta(days=50), "iv30": 0.80},  # High
            {"date": date.today() - timedelta(days=10), "iv30": 0.50}   # Middle
        ]
        upsert_history(self.db, symbol, history)
        
        # 2. Insert Today's Result (initially no rank)
        upsert_result(self.db, {"symbol": symbol, "calculated_metrics": {}})
        self.db.commit()
        
        # 3. Calculate Rank
        # Current IV = 0.50. Range = 0.80 - 0.20 = 0.60.
        # Rank = (0.50 - 0.20) / 0.60 = 0.30 / 0.60 = 0.50
        details = {"iv30_current": 0.50, "other": "data"}
        calculate_and_save_rank(self.db, symbol, date.today(), details)
        
        # 4. Verify
        res = self.db.query(ScreenResult).filter_by(symbol=symbol, date=date.today()).first()
        self.assertIsNotNone(res)
        self.assertAlmostEqual(res.raw_data.get("iv_rank"), 0.50)
        
        # Test fallback to iv_short if iv30_current missing
        details2 = {"iv_short": 0.20} # Equal to min, rank should be 0.0
        calculate_and_save_rank(self.db, symbol, date.today(), details2)
        res = self.db.query(ScreenResult).filter_by(symbol=symbol, date=date.today()).first()
        self.assertEqual(res.raw_data.get("iv_rank"), 0.0)



if __name__ == '__main__':
    unittest.main()
