from pydantic import BaseModel, Field


class ProductWasteCreate(BaseModel):
    product_id: int
    quantity: float = Field(gt=0)
    reason: str = ""
