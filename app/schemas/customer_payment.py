from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CustomerPaymentCreate(BaseModel):
    sale_id: int
    amount: float = Field(ge=0, default=0)
    discount_amount: float = Field(ge=0, default=0)
    note: Optional[str] = None
