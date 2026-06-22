from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date, time

from app.core.database import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.core.pagination import make_page
from app.core.stock import log_stock
from app.models.purchase import Purchase
from app.models.purchase_item import PurchaseItem
from app.models.product import Product
from app.schemas.purchase import PurchaseCreate
from app.models.supplier import Supplier
from sqlalchemy import desc

router = APIRouter(
    prefix="/purchases",
    tags=["Purchases"],
    dependencies=[Depends(get_current_user)]
)


@router.post("/")
def create_purchase(
    data: PurchaseCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    total = 0

    purchase = Purchase(
        supplier_id=data.supplier_id,
        total_amount=0,
        invoice_no="",
        tenant_id=tenant_id,
    )
    db.add(purchase)
    db.flush()

    date_part = datetime.now().strftime("%Y%m%d")
    purchase.invoice_no = f"PUR-{date_part}-{str(purchase.id).zfill(5)}"

    for item in data.items:
        product = db.query(Product).filter(Product.id == item.product_id, Product.tenant_id == tenant_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")

        amount = item.quantity * item.rate
        total += amount

        db.add(PurchaseItem(
            purchase_id=purchase.id,
            product_id=item.product_id,
            quantity=item.quantity,
            rate=item.rate,
            amount=amount,
            tenant_id=tenant_id,
        ))

        log_stock(
            db=db,
            product=product,
            transaction_type="PURCHASE",
            quantity=item.quantity,
            reference_id=purchase.id,
            reference_no=purchase.invoice_no,
            tenant_id=tenant_id,
        )

    purchase.total_amount = total
    db.commit()
    return {"message": "Purchase created successfully", "total": total}


@router.get("/")
def get_purchases(
    supplier_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    query = db.query(Purchase).filter(Purchase.tenant_id == tenant_id).order_by(desc(Purchase.id))
    if supplier_id:
        query = query.filter(Purchase.supplier_id == supplier_id)
    if date_from:
        query = query.filter(Purchase.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        query = query.filter(Purchase.created_at <= datetime.combine(date_to, time.max))

    total = query.count()
    purchases = query.offset((page - 1) * page_size).limit(page_size).all()

    result = []
    for p in purchases:
        supplier = db.query(Supplier).filter(Supplier.id == p.supplier_id, Supplier.tenant_id == tenant_id).first()
        result.append({
            "id": p.id,
            "invoice_no": p.invoice_no,
            "supplier_id": p.supplier_id,
            "supplier_name": supplier.name if supplier else None,
            "total_amount": p.total_amount,
            "created_at": p.created_at
        })
    return make_page(result, total, page, page_size)


@router.get("/{purchase_id}")
def get_purchase(purchase_id: int, db: Session = Depends(get_db), tenant_id: int = Depends(get_tenant_id)):
    purchase = db.query(Purchase).filter(Purchase.id == purchase_id, Purchase.tenant_id == tenant_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")

    supplier = db.query(Supplier).filter(Supplier.id == purchase.supplier_id).first()
    purchase_items = db.query(PurchaseItem).filter(PurchaseItem.purchase_id == purchase.id).all()

    items = []
    for item in purchase_items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        items.append({
            "product_id": item.product_id,
            "product_name": product.name if product else "",
            "quantity": item.quantity,
            "rate": item.rate,
            "total": item.quantity * item.rate,
        })

    return {
        "id": purchase.id,
        "supplier_name": supplier.name if supplier else "",
        "created_at": purchase.created_at,
        "total_amount": purchase.total_amount,
        "items": items,
    }
