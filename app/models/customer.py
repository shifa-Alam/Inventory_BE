from sqlalchemy import Column, Integer, String, Float
from app.core.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(150), nullable=False)

    phone = Column(String(30))

    address = Column(String(255))

    credit_limit = Column(Float, default=0)

    current_due = Column(Float, default=0)
