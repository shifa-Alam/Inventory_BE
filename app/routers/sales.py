from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date, time

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.pagination import make_page
from app.core.stock import log_stock
from app.core.payment_log import log_payment
from app.models.sales import Sale
from app.models.sales_item import SaleItem
from app.models.product import Product
from app.models.customer import Customer
from app.schemas.sales import SaleCreate
from sqlalchemy import desc

router = APIRouter(
    prefix="/sales",
    tags=["Sales"],
    dependencies=[Depends(get_current_user)]
)


def _current_user_name(current_user: dict) -> str:
    return current_user.get("sub") or current_user.get("username") or "system"


@router.post("/")
def create_sale(data: SaleCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):

    total = 0

    # 1. RESOLVE CUSTOMER
    if data.customer_id:
        customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
    else:
        customer = db.query(Customer).filter(Customer.name == "Walk-in").first()
        if not customer:
            customer = Customer(name="Walk-in", phone='', address='', credit_limit=0, opening_due=0, current_due=0)
            db.add(customer)
            db.flush()

    # 2. CREATE SALE
    sale = Sale(
        customer_id=customer.id,
        paid_amount=data.paid_amount,
        total_amount=0,
        due_amount=0,
        invoice_no=""
    )

    db.add(sale)
    db.flush()

    # 3. GENERATE INVOICE NO
    date_part = datetime.now().strftime("%Y%m%d")
    sale.invoice_no = f"INV-{date_part}-{str(sale.id).zfill(5)}"

    # 4. PROCESS ITEMS
    for item in data.items:

        product = db.query(Product).with_for_update().filter(
            Product.id == item.product_id
        ).first()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # STOCK CHECK
        if product.current_stock < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough stock for {product.name}"
            )

        amount = item.quantity * item.rate
        total += amount

        db.add(SaleItem(
            sale_id=sale.id,
            product_id=item.product_id,
            quantity=item.quantity,
            rate=item.rate,
            amount=amount
        ))

        log_stock(
            db=db,
            product=product,
            transaction_type="SALE",
            quantity=item.quantity,
            reference_id=sale.id,
            reference_no=sale.invoice_no
        )

    # 5. FINAL CALCULATION
    discount = data.discount or 0
    if discount > total:
        raise HTTPException(status_code=400, detail="Discount exceeds order total")

    net_total = total - discount

    if data.paid_amount > net_total:
        raise HTTPException(status_code=400, detail="Paid amount exceeds order total")

    due = net_total - data.paid_amount

    sale.total_amount = net_total
    sale.discount_amount = discount
    sale.due_amount = due

    # UPDATE CUSTOMER DUE
    customer.current_due += due

    # 7. LOG TO CENTRAL PAYMENT LEDGER (initial payment only)
    if data.paid_amount > 0:
        log_payment(
            db=db,
            transaction_type="SALE_PAYMENT",
            amount=data.paid_amount,
            reference_no=sale.invoice_no,
            sale_id=sale.id,
            customer_id=data.customer_id,
            note=f"Payment on sale {sale.invoice_no}",
            created_by=_current_user_name(current_user),
        )

    if discount > 0:
        log_payment(
            db=db,
            transaction_type="DISCOUNT",
            amount=discount,
            reference_no=sale.invoice_no,
            sale_id=sale.id,
            customer_id=data.customer_id,
            note=f"Discount on sale {sale.invoice_no}",
            created_by=_current_user_name(current_user),
        )

    # 6. FINAL SAVE
    db.commit()
    db.refresh(sale)

    return {
        "message": "Sale created successfully",
        "id": sale.id,
        "invoice_no": sale.invoice_no,
        "subtotal": total,
        "discount": discount,
        "total": net_total,
        "paid": data.paid_amount,
        "due": due
    }


@router.get("/")
def get_sales(
    customer_id: Optional[int] = Query(None),
    invoice_no: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    has_due: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    query = db.query(Sale).order_by(desc(Sale.id))

    if customer_id:
        query = query.filter(Sale.customer_id == customer_id)
    if invoice_no:
        query = query.filter(Sale.invoice_no.ilike(f"%{invoice_no}%"))
    if date_from:
        query = query.filter(Sale.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        query = query.filter(Sale.created_at <= datetime.combine(date_to, time.max))
    if has_due is True:
        query = query.filter(Sale.due_amount > 0)
    elif has_due is False:
        query = query.filter(Sale.due_amount == 0)

    total = query.count()
    sales = query.offset((page - 1) * page_size).limit(page_size).all()

    result = []
    for s in sales:
        customer_name = None
        if s.customer_id:
            customer = db.query(Customer).filter(Customer.id == s.customer_id).first()
            if customer:
                customer_name = customer.name

        items = db.query(SaleItem).filter(SaleItem.sale_id == s.id).all()
        item_list = []
        for i in items:
            product = db.query(Product).filter(Product.id == i.product_id).first()
            item_list.append({
                "product_id": i.product_id,
                "product_name": product.name if product else None,
                "quantity": i.quantity,
                "rate": i.rate,
                "total": i.quantity * i.rate
            })

        result.append({
            "id": s.id,
            "invoice_no": s.invoice_no,
            "customer_id": s.customer_id,
            "customer_name": customer_name,
            "paid_amount": s.paid_amount,
            "discount_amount": s.discount_amount if hasattr(s, 'discount_amount') else 0,
            "total_amount": s.total_amount,
            "subtotal": round((s.total_amount or 0) + (s.discount_amount or 0), 2),
            "due_amount": s.due_amount,
            "created_at": s.created_at,
            "items": item_list
        })

    return make_page(result, total, page, page_size)


@router.get("/{sale_id}")
def get_sale(sale_id: int, db: Session = Depends(get_db)):

    sale = db.query(Sale).filter(Sale.id == sale_id).first()

    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    items = db.query(SaleItem).filter(SaleItem.sale_id == sale.id).all()

    customer_name = None
    customer_phone = None
    customer_address = None
    if sale.customer_id:
        customer = db.query(Customer).filter(Customer.id == sale.customer_id).first()
        if customer:
            customer_name = customer.name
            customer_phone = customer.phone
            customer_address = customer.address

    item_list = []
    for i in items:
        product = db.query(Product).filter(Product.id == i.product_id).first()
        item_list.append({
            "product_id": i.product_id,
            "product_name": product.name if product else None,
            "quantity": i.quantity,
            "rate": i.rate,
            "mrp": (product.mrp or 0) if product else 0,
            "returned_qty": i.returned_qty or 0,
            "total": i.quantity * i.rate
        })

    discount_amount = sale.discount_amount if hasattr(sale, 'discount_amount') else 0
    return {
        "id": sale.id,
        "invoice_no": sale.invoice_no,
        "customer_id": sale.customer_id,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "customer_address": customer_address,
        "subtotal": round((sale.total_amount or 0) + (discount_amount or 0), 2),
        "discount_amount": discount_amount or 0,
        "total_amount": sale.total_amount,
        "paid_amount": sale.paid_amount,
        "due_amount": sale.due_amount,
        "created_at": sale.created_at,
        "items": item_list
    }
