import unittest
from unittest.mock import MagicMock, patch
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Base, Stock, ScreenResult
from ingest import upsert_stock, upsert_result

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

if __name__ == '__main__':
    unittest.main()
