from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, String
from datetime import datetime

from app.core.database import Base


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)

    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    invoice_no = Column(String(50), nullable=False)
    total_amount = Column(Float, default=0)

    created_at = Column(DateTime, default=datetime.now)
