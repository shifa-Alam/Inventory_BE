from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import require_system_admin
from app.models.tenant import Tenant

router = APIRouter(prefix="/tenants", tags=["Tenants"])


class TenantCreate(BaseModel):
    name: str


class TenantUpdate(BaseModel):
    name: str


@router.post("/")
def create_tenant(
    data: TenantCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(require_system_admin)
):
    tenant = Tenant(name=data.name)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return {"id": tenant.id, "name": tenant.name, "is_active": tenant.is_active, "created_at": tenant.created_at}


@router.get("/")
def list_tenants(
    db: Session = Depends(get_db),
    _: dict = Depends(require_system_admin)
):
    tenants = db.query(Tenant).order_by(Tenant.id).all()
    return [{"id": t.id, "name": t.name, "is_active": t.is_active, "created_at": t.created_at} for t in tenants]


@router.get("/{tenant_id}")
def get_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_system_admin)
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {"id": tenant.id, "name": tenant.name, "is_active": tenant.is_active, "created_at": tenant.created_at}


@router.patch("/{tenant_id}")
def update_tenant(
    tenant_id: int,
    data: TenantUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(require_system_admin)
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant.name = data.name
    db.commit()
    return {"message": "Tenant updated", "id": tenant.id, "name": tenant.name}


@router.delete("/{tenant_id}/deactivate")
def deactivate_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_system_admin)
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant.is_active = False
    db.commit()
    return {"message": "Tenant deactivated"}
