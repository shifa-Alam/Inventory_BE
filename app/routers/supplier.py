from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.deps import get_current_user, get_tenant_id
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
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    query = db.query(Supplier).filter(Supplier.tenant_id == tenant_id)
    if name:
        query = query.filter(Supplier.name.ilike(f"%{name}%"))
    total = query.count()
    suppliers = query.offset((page - 1) * page_size).limit(page_size).all()
    return make_page(suppliers, total, page, page_size)


@router.post("/")
def create_supplier(
    data: SupplierCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    supplier = Supplier(**data.model_dump(), tenant_id=tenant_id)
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier
