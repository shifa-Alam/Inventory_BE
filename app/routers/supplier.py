from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.pagination import make_page
from app.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate

router = APIRouter(
    prefix="/suppliers",
    tags=["Suppliers"],
    dependencies=[Depends(get_current_user)]
)


@router.get("/")
def get_suppliers(
    name: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    query = db.query(Supplier)

    if name:
        query = query.filter(Supplier.name.ilike(f"%{name}%"))

    total = query.count()
    suppliers = query.offset((page - 1) * page_size).limit(page_size).all()
    return make_page(suppliers, total, page, page_size)


@router.post("/")
def create_supplier(data: SupplierCreate, db: Session = Depends(get_db)):
    supplier = Supplier(**data.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier
