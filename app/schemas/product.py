from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    sku: str = Field(min_length=1, max_length=50)
    category_id: int
    purchase_price: float = Field(ge=0, default=0)
    sale_price: float = Field(ge=0, default=0)
    current_stock: float = Field(ge=0, default=0)


class ProductUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    sku: str = Field(min_length=1, max_length=50)
    category_id: int
    purchase_price: float = Field(ge=0, default=0)
    sale_price: float = Field(ge=0, default=0)


class ProductResponse(ProductCreate):
    id: int

    class Config:
        from_attributes = True
