from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.pagination import make_page
from app.core.payment_log import log_payment
from app.models.customer_payment import CustomerPayment
from app.models.sales import Sale
from app.models.customer import Customer
from app.schemas.customer_payment import CustomerPaymentCreate
from sqlalchemy import func

router = APIRouter(
    prefix="/payments",
    tags=["Payments"],
    dependencies=[Depends(get_current_user)]
)


def _gen_ref(db: Session) -> str:
    count = db.query(func.count(CustomerPayment.id)).scalar() or 0
    return f"PAY-{count + 1:05d}"


@router.post("/invoice")
def pay_invoice(data: CustomerPaymentCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if data.amount == 0 and data.discount_amount == 0:
        raise HTTPException(status_code=400, detail="Amount or discount must be greater than zero")

    sale = db.query(Sale).filter(Sale.id == data.sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    if sale.due_amount <= 0:
        raise HTTPException(status_code=400, detail="Invoice has no outstanding due")

    total_reduction = data.amount + data.discount_amount
    if total_reduction > sale.due_amount + 0.001:
        raise HTTPException(
            status_code=400,
            detail=f"Total (payment + discount) exceeds due amount of {sale.due_amount:.2f}"
        )

    payment = CustomerPayment(
        sale_id=data.sale_id,
        customer_id=sale.customer_id,
        amount=data.amount,
        discount_amount=data.discount_amount,
        note=data.note,
        reference_no=_gen_ref(db),
    )
    db.add(payment)

    sale.paid_amount = round(sale.paid_amount + data.amount, 2)
    sale.discount_amount = round(getattr(sale, 'discount_amount', 0) + data.discount_amount, 2)
    sale.due_amount = round(max(0, sale.due_amount - total_reduction), 2)

    if sale.customer_id:
        customer = db.query(Customer).filter(Customer.id == sale.customer_id).first()
        if customer:
            customer.current_due = round(max(0, customer.current_due - total_reduction), 2)

    operator = current_user.get("sub") or current_user.get("username") or "system"
    if data.amount > 0:
        log_payment(
            db=db,
            transaction_type="DUE_PAYMENT",
            amount=data.amount,
            reference_no=payment.reference_no,
            sale_id=data.sale_id,
            customer_id=sale.customer_id,
            note=data.note or f"Due payment for {sale.invoice_no}",
            created_by=operator,
        )
    if data.discount_amount > 0:
        log_payment(
            db=db,
            transaction_type="DISCOUNT",
            amount=-data.discount_amount,
            reference_no=payment.reference_no,
            sale_id=data.sale_id,
            customer_id=sale.customer_id,
            note=data.note or f"Discount on {sale.invoice_no}",
            created_by=operator,
        )

    db.commit()
    db.refresh(payment)
    return {
        "id": payment.id,
        "reference_no": payment.reference_no,
        "sale_id": sale.id,
        "invoice_no": sale.invoice_no,
        "amount": payment.amount,
        "discount_amount": payment.discount_amount,
        "sale_due_remaining": sale.due_amount,
        "created_at": payment.created_at,
    }


@router.get("/invoice")
def list_payments(
    sale_id: Optional[int] = Query(None),
    customer_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    query = (
        db.query(CustomerPayment, Sale.invoice_no, Customer.name.label("customer_name"))
        .join(Sale, CustomerPayment.sale_id == Sale.id)
        .outerjoin(Customer, CustomerPayment.customer_id == Customer.id)
    )

    if sale_id:
        query = query.filter(CustomerPayment.sale_id == sale_id)
    if customer_id:
        query = query.filter(CustomerPayment.customer_id == customer_id)
    if date_from:
        query = query.filter(CustomerPayment.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(CustomerPayment.created_at <= datetime.combine(date_to, datetime.max.time()))

    query = query.order_by(CustomerPayment.created_at.desc())
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()

    items = [{
        "id": p.id,
        "sale_id": p.sale_id,
        "invoice_no": invoice_no,
        "customer_name": customer_name or "—",
        "amount": p.amount,
        "discount_amount": p.discount_amount,
        "note": p.note,
        "reference_no": p.reference_no,
        "created_at": p.created_at,
    } for p, invoice_no, customer_name in rows]

    return make_page(items, total, page, page_size)


@router.get("/invoice/summary")
def payment_summary(db: Session = Depends(get_db)):
    today = date.today()
    today_total = db.query(func.sum(CustomerPayment.amount)).filter(
        func.date(CustomerPayment.created_at) == today
    ).scalar() or 0
    all_total = db.query(func.sum(CustomerPayment.amount)).scalar() or 0
    all_discount = db.query(func.sum(CustomerPayment.discount_amount)).scalar() or 0
    count = db.query(func.count(CustomerPayment.id)).scalar() or 0
    pending = db.query(func.count(Sale.id)).filter(Sale.due_amount > 0).scalar() or 0
    return {
        "today_collection": round(today_total, 2),
        "total_collection": round(all_total, 2),
        "total_discount": round(all_discount, 2),
        "total_transactions": count,
        "pending_invoices": pending,
    }
