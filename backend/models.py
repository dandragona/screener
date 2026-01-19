from sqlalchemy import Column, String, Float, Date, Integer, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import date
from database import Base

class Stock(Base):
    __tablename__ = "stocks"

    symbol = Column(String, primary_key=True, index=True)
    company_name = Column(String, nullable=True)
    sector = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    last_updated = Column(DateTime(timezone=True), onupdate=func.now())

    results = relationship("ScreenResult", back_populates="stock")

class ScreenResult(Base):
    __tablename__ = "screen_results"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, default=date.today, index=True)
    symbol = Column(String, ForeignKey("stocks.symbol"), index=True)
    
    score = Column(Float, index=True)
    
    # Key metrics we might want to filter on specifically in SQL
    p_fcf = Column(Float, nullable=True)
    peg_ratio = Column(Float, nullable=True)
    market_cap = Column(Float, nullable=True)
    
    # All other details stored here
    raw_data = Column(JSON, nullable=True)

    stock = relationship("Stock", back_populates="results")
