from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from datetime import datetime
from app.core.database import Base


class CustomerPayment(Base):
    __tablename__ = "customer_payments"

    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    amount = Column(Float, default=0)
    discount_amount = Column(Float, default=0)
    note = Column(String(255), nullable=True)
    reference_no = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
