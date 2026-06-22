from sqlalchemy import Column, Integer, Float, ForeignKey
from app.core.database import Base


class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    id = Column(Integer, primary_key=True, index=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Float)
    rate = Column(Float)
    amount = Column(Float)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
