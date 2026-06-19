from pydantic import BaseModel, Field
from typing import List


class SaleReturnItemCreate(BaseModel):
    product_id: int
    quantity: float = Field(gt=0)
    rate: float = Field(gt=0)


class SaleReturnCreate(BaseModel):
    sale_id: int
    customer_id: int
    reason: str = ""
    items: List[SaleReturnItemCreate] = Field(min_length=1)
