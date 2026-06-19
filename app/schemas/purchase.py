from pydantic import BaseModel, Field
from typing import List


class PurchaseItemCreate(BaseModel):
    product_id: int
    quantity: float = Field(gt=0)
    rate: float = Field(gt=0)
    invoice_no: str = ''


class PurchaseCreate(BaseModel):
    supplier_id: int
    items: List[PurchaseItemCreate] = Field(min_length=1)
