from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.core.pagination import make_page
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin

router = APIRouter(prefix="/auth", tags=["Auth"])


# ROLES
@router.get("/roles")
def get_roles(_: dict = Depends(get_current_user)):
    return [
        {"value": "system_admin", "label": "System Admin"},
        {"value": "admin",        "label": "Admin"},
        {"value": "staff",        "label": "Staff"},
    ]


# LIST USERS (admin only)
@router.get("/users/")
def list_users(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin)
):
    query = db.query(User)
    total = query.count()
    users = query.offset((page - 1) * page_size).limit(page_size).all()
    return make_page(
        [{"id": u.id, "username": u.username, "role": u.role} for u in users],
        total, page, page_size
    )


# UPDATE USER (admin only)
@router.put("/users/{user_id}")
def update_user(user_id: int, user: UserCreate, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db_user.username = user.username
    db_user.role = user.role
    if user.password:
        db_user.password = hash_password(user.password)
    db.commit()
    return {"message": "User updated successfully"}


# DELETE USER (admin only)
@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}


# REGISTER (admin only)
@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    existing_user = db.query(User).filter(
        User.username == user.username).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    new_user = User(
        username=user.username,
        password=hash_password(user.password),
        role=user.role
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

    token = create_access_token(
        data={"sub": db_user.username, "role": db_user.role}
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }
