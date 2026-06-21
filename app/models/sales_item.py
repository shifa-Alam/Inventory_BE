from sqlalchemy import Column, Integer, Float, ForeignKey
from app.core.database import Base


class SaleItem(Base):
    __tablename__ = "sale_items"

    id = Column(Integer, primary_key=True, index=True)

    sale_id = Column(Integer, ForeignKey("sales.id"))

    product_id = Column(Integer, ForeignKey("products.id"))

    quantity = Column(Float)

    rate = Column(Float)

    amount = Column(Float)

    returned_qty = Column(Float, default=0, nullable=False, server_default="0")
