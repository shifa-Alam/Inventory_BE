from sqlalchemy import Column, Integer, String
from app.core.database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(150), nullable=False)

    phone = Column(String(30))

    address = Column(String(255))
