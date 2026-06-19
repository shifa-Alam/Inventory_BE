from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class CategoryResponse(CategoryCreate):
    id: int

    class Config:
        from_attributes = True
