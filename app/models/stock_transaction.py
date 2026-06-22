from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, String, Text
from datetime import datetime
from app.core.database import Base


class StockTransaction(Base):
    __tablename__ = "stock_transactions"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    transaction_type = Column(String(20), nullable=False)  # PURCHASE, SALE, RETURN, WASTE
    reference_id = Column(Integer)
    reference_no = Column(String(50))
    quantity = Column(Float, nullable=False)
    stock_before = Column(Float)
    stock_after = Column(Float)
    note = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
