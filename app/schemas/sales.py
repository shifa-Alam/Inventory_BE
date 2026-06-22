from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date


class SaleItemCreate(BaseModel):
    product_id: int
    quantity: float = Field(gt=0)
    rate: float = Field(gt=0)


class SaleCreate(BaseModel):
    customer_id: Optional[int] = None
    paid_amount: float = Field(ge=0, default=0)
    discount: float = Field(ge=0, default=0)
    invoice_no: str = ''
    delivery_date: Optional[date] = None
    items: List[SaleItemCreate] = Field(min_length=1)
