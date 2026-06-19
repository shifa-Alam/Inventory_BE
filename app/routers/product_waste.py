from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from datetime import datetime, date, time

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.pagination import make_page
from app.core.stock import log_stock
from app.models.product_waste import ProductWaste
from app.models.product import Product
from app.schemas.product_waste import ProductWasteCreate

router = APIRouter(
    prefix="/product-wastes",
    tags=["Product Wastes"],
    dependencies=[Depends(get_current_user)]
)


@router.post("/")
def create_waste(data: ProductWasteCreate, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.current_stock < data.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough stock. Available: {product.current_stock}"
        )

    waste = ProductWaste(
        product_id=data.product_id,
        quantity=data.quantity,
        reason=data.reason,
        waste_no=""
    )
    db.add(waste)
    db.flush()

    date_part = datetime.now().strftime("%Y%m%d")
    waste.waste_no = f"WST-{date_part}-{str(waste.id).zfill(5)}"
    db.flush()

    log_stock(
        db=db,
        product=product,
        transaction_type="WASTE",
        quantity=data.quantity,
        reference_id=waste.id,
        reference_no=waste.waste_no,
        note=data.reason
    )

    db.commit()
    db.refresh(waste)

    return {
        "message": "Waste recorded successfully",
        "waste_no": waste.waste_no,
        "product": product.name,
        "quantity_wasted": data.quantity,
        "remaining_stock": product.current_stock
    }


@router.get("/")
def get_wastes(
    product_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    query = db.query(ProductWaste).order_by(desc(ProductWaste.id))

    if product_id:
        query = query.filter(ProductWaste.product_id == product_id)
    if date_from:
        query = query.filter(ProductWaste.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        query = query.filter(ProductWaste.created_at <= datetime.combine(date_to, time.max))

    total = query.count()
    wastes = query.offset((page - 1) * page_size).limit(page_size).all()

    result = []
    for w in wastes:
        product = db.query(Product).filter(Product.id == w.product_id).first()
        result.append({
            "id": w.id,
            "waste_no": w.waste_no,
            "product_id": w.product_id,
            "product_name": product.name if product else None,
            "quantity": w.quantity,
            "reason": w.reason,
            "created_at": w.created_at
        })

    return make_page(result, total, page, page_size)


@router.get("/{waste_id}")
def get_waste(waste_id: int, db: Session = Depends(get_db)):
    waste = db.query(ProductWaste).filter(ProductWaste.id == waste_id).first()
    if not waste:
        raise HTTPException(status_code=404, detail="Waste record not found")

    product = db.query(Product).filter(Product.id == waste.product_id).first()

    return {
        "id": waste.id,
        "waste_no": waste.waste_no,
        "product_id": waste.product_id,
        "product_name": product.name if product else None,
        "quantity": waste.quantity,
        "reason": waste.reason,
        "created_at": waste.created_at
    }
