from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.core.pagination import make_page
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate
from app.schemas.customer import CustomerUpdate

router = APIRouter(
    prefix="/customers",
    tags=["Customers"],
    dependencies=[Depends(get_current_user)]
)


@router.get("/")
def get_customers(
    name: Optional[str] = Query(None),
    has_due: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    query = db.query(Customer)

    if name:
        query = query.filter(Customer.name.ilike(f"%{name}%"))
    if has_due is True:
        query = query.filter(Customer.current_due > 0)
    elif has_due is False:
        query = query.filter(Customer.current_due == 0)

    total = query.count()
    customers = query.offset((page - 1) * page_size).limit(page_size).all()
    return make_page(customers, total, page, page_size)


@router.post("/")
def create_customer(data: CustomerCreate, db: Session = Depends(get_db)):
    customer = Customer(**data.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.put("/{id}")
def update_customer(id: int, customer: CustomerUpdate, db: Session = Depends(get_db)):
    db_customer = db.query(Customer).filter(Customer.id == id).first()

    if not db_customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    db_customer.name = customer.name
    db_customer.phone = customer.phone
    db_customer.address = customer.address
    db_customer.credit_limit = customer.credit_limit

    db.commit()
    db.refresh(db_customer)
    return db_customer


@router.delete("/{id}")
def delete_customer(id: int, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    customer = db.query(Customer).filter(Customer.id == id).first()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    db.delete(customer)
    db.commit()
    return {"message": "Customer deleted successfully"}
