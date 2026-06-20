from sqlalchemy import Column, Integer, String, Float, ForeignKey
from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(150), nullable=False)

    sku = Column(String(50), unique=True, index=True)

    category_id = Column(Integer, ForeignKey("categories.id"))

    purchase_price = Column(Float, default=0)

    sale_price = Column(Float, default=0)

    mrp = Column(Float, default=0)

    current_stock = Column(Float, default=0)
