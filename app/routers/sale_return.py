from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from datetime import datetime, date, time

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.pagination import make_page
from app.core.stock import log_stock
from app.core.payment_log import log_payment
from app.models.sale_return import SaleReturn, SaleReturnItem
from app.models.sales import Sale
from app.models.sales_item import SaleItem
from app.models.product import Product
from app.models.customer import Customer
from app.schemas.sale_return import SaleReturnCreate

router = APIRouter(
    prefix="/sale-returns",
    tags=["Sale Returns"],
    dependencies=[Depends(get_current_user)]
)


@router.post("/")
def create_sale_return(data: SaleReturnCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    sale = db.query(Sale).filter(Sale.id == data.sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    if sale.customer_id != data.customer_id:
        raise HTTPException(status_code=400, detail="Customer does not match the original sale")

    # Lock the sale_items rows so concurrent requests can't double-return
    original_items = (
        db.query(SaleItem)
        .filter(SaleItem.sale_id == sale.id)
        .with_for_update()
        .all()
    )
    item_map = {i.product_id: i for i in original_items}

    for item in data.items:
        if item.product_id not in item_map:
            raise HTTPException(
                status_code=400,
                detail=f"Product {item.product_id} was not in the original sale"
            )
        si = item_map[item.product_id]
        remaining = si.quantity - (si.returned_qty or 0)
        if remaining <= 0:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            name = product.name if product else f"Product {item.product_id}"
            raise HTTPException(
                status_code=400,
                detail=f'"{name}" has already been fully returned for this invoice'
            )
        if item.quantity > remaining:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            name = product.name if product else f"Product {item.product_id}"
            raise HTTPException(
                status_code=400,
                detail=f'Return qty for "{name}" exceeds remaining returnable qty ({remaining})'
            )

    sale_return = SaleReturn(
        sale_id=data.sale_id,
        customer_id=data.customer_id,
        reason=data.reason,
        total_amount=0,
        return_no=""
    )
    db.add(sale_return)
    db.flush()

    date_part = datetime.now().strftime("%Y%m%d")
    sale_return.return_no = f"RET-{date_part}-{str(sale_return.id).zfill(5)}"
    db.flush()

    total = 0
    for item in data.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")

        amount = item.quantity * item.rate
        total += amount

        db.add(SaleReturnItem(
            return_id=sale_return.id,
            product_id=item.product_id,
            quantity=item.quantity,
            rate=item.rate,
            amount=amount
        ))

        # Update returned_qty on the original SaleItem (database-level tracking)
        si = item_map[item.product_id]
        si.returned_qty = (si.returned_qty or 0) + item.quantity

        log_stock(
            db=db,
            product=product,
            transaction_type="RETURN",
            quantity=item.quantity,
            reference_id=sale_return.id,
            reference_no=sale_return.return_no,
            note=data.reason
        )

    # Apply proportional discount to refund
    discount_amount = sale.discount_amount or 0
    subtotal_original = (sale.total_amount or 0) + discount_amount
    discount_rate = discount_amount / subtotal_original if subtotal_original else 0
    net_refund = round(total * (1 - discount_rate), 2)

    sale_return.total_amount = net_refund

    # Reduce customer due (can't go below 0)
    customer.current_due = max(0, customer.current_due - net_refund)

    # Log to central payment ledger as negative (cash out / refund)
    log_payment(
        db=db,
        transaction_type="RETURN",
        amount=-net_refund,
        reference_no=sale_return.return_no,
        sale_id=data.sale_id,
        customer_id=data.customer_id,
        note=data.reason or f"Return against sale {sale.invoice_no}",
        created_by=current_user.get("sub") or current_user.get("username") or "system",
    )

    db.commit()
    db.refresh(sale_return)

    return {
        "message": "Sale return recorded successfully",
        "return_no": sale_return.return_no,
        "gross_returned": total,
        "discount_deduction": round(total * discount_rate, 2),
        "refund_amount": net_refund
    }


@router.get("/")
def get_sale_returns(
    customer_id: Optional[int] = Query(None),
    sale_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    query = db.query(SaleReturn).order_by(desc(SaleReturn.id))

    if customer_id:
        query = query.filter(SaleReturn.customer_id == customer_id)
    if sale_id:
        query = query.filter(SaleReturn.sale_id == sale_id)
    if date_from:
        query = query.filter(SaleReturn.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        query = query.filter(SaleReturn.created_at <= datetime.combine(date_to, time.max))

    total = query.count()
    returns = query.offset((page - 1) * page_size).limit(page_size).all()

    result = []
    for r in returns:
        customer = db.query(Customer).filter(Customer.id == r.customer_id).first()
        items = db.query(SaleReturnItem).filter(SaleReturnItem.return_id == r.id).all()

        item_list = []
        for i in items:
            product = db.query(Product).filter(Product.id == i.product_id).first()
            item_list.append({
                "product_id": i.product_id,
                "product_name": product.name if product else None,
                "quantity": i.quantity,
                "rate": i.rate,
                "amount": i.amount
            })

        sale_for_inv = db.query(Sale).filter(Sale.id == r.sale_id).first()
        result.append({
            "id": r.id,
            "return_no": r.return_no,
            "sale_id": r.sale_id,
            "invoice_no": sale_for_inv.invoice_no if sale_for_inv else None,
            "customer_name": customer.name if customer else None,
            "total_amount": r.total_amount,
            "reason": r.reason,
            "created_at": r.created_at,
            "items": item_list
        })

    return make_page(result, total, page, page_size)


@router.get("/{return_id}")
def get_sale_return(return_id: int, db: Session = Depends(get_db)):
    sale_return = db.query(SaleReturn).filter(SaleReturn.id == return_id).first()
    if not sale_return:
        raise HTTPException(status_code=404, detail="Sale return not found")

    items = db.query(SaleReturnItem).filter(SaleReturnItem.return_id == return_id).all()
    customer = db.query(Customer).filter(Customer.id == sale_return.customer_id).first()

    item_list = []
    for i in items:
        product = db.query(Product).filter(Product.id == i.product_id).first()
        item_list.append({
            "product_id": i.product_id,
            "product_name": product.name if product else None,
            "quantity": i.quantity,
            "rate": i.rate,
            "amount": i.amount
        })

    return {
        "id": sale_return.id,
        "return_no": sale_return.return_no,
        "sale_id": sale_return.sale_id,
        "customer_name": customer.name if customer else None,
        "total_amount": sale_return.total_amount,
        "reason": sale_return.reason,
        "created_at": sale_return.created_at,
        "items": item_list
    }
