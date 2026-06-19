from pydantic import BaseModel, Field
from typing import List


class SaleItemCreate(BaseModel):
    product_id: int
    quantity: float = Field(gt=0)
    rate: float = Field(gt=0)


class SaleCreate(BaseModel):
    customer_id: int
    paid_amount: float = Field(ge=0, default=0)
    invoice_no: str = ''
    items: List[SaleItemCreate] = Field(min_length=1)
