from pydantic import BaseModel, Field


class CustomerBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    phone: str | None = None
    address: str | None = None
    credit_limit: float = Field(ge=0, default=0)


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(CustomerBase):
    pass


class CustomerResponse(CustomerBase):
    id: int
    current_due: float

    class Config:
        from_attributes = True
