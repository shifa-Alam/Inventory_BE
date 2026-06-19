from pydantic import BaseModel, Field


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    phone: str | None = None
    address: str | None = None


class SupplierResponse(SupplierCreate):
    id: int

    class Config:
        from_attributes = True
