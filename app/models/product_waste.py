from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, String, Text
from datetime import datetime
from app.core.database import Base


class ProductWaste(Base):
    __tablename__ = "product_wastes"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Float)
    reason = Column(Text)
    waste_no = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
