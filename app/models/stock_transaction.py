from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, String, Text
from datetime import datetime
from app.core.database import Base


class StockTransaction(Base):
    __tablename__ = "stock_transactions"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    transaction_type = Column(String(20), nullable=False)  # PURCHASE, SALE, RETURN, WASTE
    reference_id = Column(Integer)       # id of the source record
    reference_no = Column(String(50))    # invoice_no / return_no / waste_no
    quantity = Column(Float, nullable=False)  # always positive
    stock_before = Column(Float)
    stock_after = Column(Float)
    note = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
