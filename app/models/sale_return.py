from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, String, Text
from datetime import datetime
from app.core.database import Base


class SaleReturn(Base):
    __tablename__ = "sale_returns"

    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"))
    customer_id = Column(Integer, ForeignKey("customers.id"))
    return_no = Column(String(50), nullable=False)
    total_amount = Column(Float, default=0)
    reason = Column(Text)
    created_at = Column(DateTime, default=datetime.now)


class SaleReturnItem(Base):
    __tablename__ = "sale_return_items"

    id = Column(Integer, primary_key=True, index=True)
    return_id = Column(Integer, ForeignKey("sale_returns.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Float)
    rate = Column(Float)
    amount = Column(Float)
