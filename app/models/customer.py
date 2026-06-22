from sqlalchemy import Column, Integer, String, Float, ForeignKey
from app.core.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    phone = Column(String(30))
    address = Column(String(255))
    credit_limit = Column(Float, default=0)
    current_due = Column(Float, default=0)
    opening_due = Column(Float, default=0)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
