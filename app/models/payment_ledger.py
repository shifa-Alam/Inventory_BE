from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from datetime import datetime
from app.core.database import Base


class PaymentLedger(Base):
    __tablename__ = "payment_ledger"

    id = Column(Integer, primary_key=True, index=True)
    # SALE_PAYMENT | DUE_PAYMENT | DISCOUNT | RETURN
    transaction_type = Column(String(30), nullable=False)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    reference_no = Column(String(100), nullable=True)   # invoice_no / return_no / PAY-ref
    amount = Column(Float, default=0)                   # positive = cash in, negative = refund
    note = Column(String(255), nullable=True)
    created_by = Column(String(100), nullable=True)     # username from token
    created_at = Column(DateTime, default=datetime.now)
