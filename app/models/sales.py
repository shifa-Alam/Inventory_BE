from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, String
from datetime import datetime
from app.core.database import Base


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    total_amount = Column(Float, default=0)
    paid_amount = Column(Float, default=0)
    discount_amount = Column(Float, default=0)
    due_amount = Column(Float, default=0)
    invoice_no = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
