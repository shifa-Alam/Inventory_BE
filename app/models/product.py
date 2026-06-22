from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, UniqueConstraint
from app.core.database import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint('sku', 'tenant_id', name='uq_product_sku_tenant'),)

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    sku = Column(String(50), index=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    purchase_price = Column(Float, default=0)
    sale_price = Column(Float, default=0)
    mrp = Column(Float, default=0)
    current_stock = Column(Float, default=0)
    is_active = Column(Boolean, default=True, nullable=False, server_default="1")
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
