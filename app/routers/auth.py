from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin, require_system_admin
from app.core.pagination import make_page
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.models.tenant import Tenant
from app.schemas.user import UserCreate, UserLogin

router = APIRouter(prefix="/auth", tags=["Auth"])


# ROLES
@router.get("/roles")
def get_roles(current_user: dict = Depends(get_current_user)):
    role = current_user.get("role")
    all_roles = [
        {"value": "system_admin", "label": "System Admin"},
        {"value": "admin",        "label": "Admin"},
        {"value": "staff",        "label": "Staff"},
    ]
    # Non-system_admin can only create staff
    if role != "system_admin":
        return [r for r in all_roles if r["value"] == "staff"]
    return all_roles


# LIST USERS (admin only — scoped to tenant)
@router.get("/users/")
def list_users(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    query = db.query(User)
    if current_user.get("role") != "system_admin":
        query = query.filter(User.tenant_id == current_user.get("tenant_id"))
    total = query.count()
    users = query.offset((page - 1) * page_size).limit(page_size).all()
    return make_page(
        [{"id": u.id, "username": u.username, "role": u.role, "tenant_id": u.tenant_id} for u in users],
        total, page, page_size
    )


# UPDATE USER (admin only — scoped to tenant)
@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    query = db.query(User).filter(User.id == user_id)
    if current_user.get("role") != "system_admin":
        query = query.filter(User.tenant_id == current_user.get("tenant_id"))
    db_user = query.first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db_user.username = user.username
    db_user.role = user.role
    if user.password:
        db_user.password = hash_password(user.password)
    db.commit()
    return {"message": "User updated successfully"}


# DELETE USER (admin only — scoped to tenant)
@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    query = db.query(User).filter(User.id == user_id)
    if current_user.get("role") != "system_admin":
        query = query.filter(User.tenant_id == current_user.get("tenant_id"))
    user = query.first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}


# REGISTER (admin only)
@router.post("/register")
def register(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    role = current_user.get("role")

    if role == "system_admin":
        if not user.tenant_id:
            raise HTTPException(status_code=400, detail="tenant_id is required when system_admin creates a user")
        tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id, Tenant.is_active == True).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found or inactive")
        assigned_tenant_id = user.tenant_id
    else:
        # admin — can only create staff for their own tenant
        if user.role not in ("staff",):
            raise HTTPException(status_code=403, detail="Admin can only create staff users")
        assigned_tenant_id = current_user.get("tenant_id")

    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    new_user = User(
        username=user.username,
        password=hash_password(user.password),
        role=user.role,
        tenant_id=assigned_tenant_id,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully"}


# LOGIN
@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()

    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token(data={
        "sub": db_user.username,
        "role": db_user.role,
        "tenant_id": db_user.tenant_id,
    })

    return {
        "access_token": token,
        "token_type": "bearer"
    }
