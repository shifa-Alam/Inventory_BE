from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case
from typing import Optional
from datetime import datetime, date

from app.core.database import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.core.pagination import make_page
from app.models.payment_ledger import PaymentLedger
from app.models.customer import Customer
from app.models.sales import Sale

router = APIRouter(
    prefix="/payment-ledger",
    tags=["Payment Ledger"],
    dependencies=[Depends(get_current_user)]
)

TYPES = ["SALE_PAYMENT", "DUE_PAYMENT", "DISCOUNT", "RETURN"]


@router.get("/")
def list_ledger(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    transaction_type: Optional[str] = Query(None),
    customer_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=500),
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    query = (
        db.query(PaymentLedger, Customer.name.label("customer_name"))
        .outerjoin(Customer, PaymentLedger.customer_id == Customer.id)
        .filter(PaymentLedger.tenant_id == tenant_id)
        .order_by(desc(PaymentLedger.id))
    )
    if date_from:
        query = query.filter(PaymentLedger.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(PaymentLedger.created_at <= datetime.combine(date_to, datetime.max.time()))
    if transaction_type and transaction_type in TYPES:
        query = query.filter(PaymentLedger.transaction_type == transaction_type)
    if customer_id:
        query = query.filter(PaymentLedger.customer_id == customer_id)

    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()

    items = [{
        "id": p.id,
        "transaction_type": p.transaction_type,
        "sale_id": p.sale_id,
        "customer_id": p.customer_id,
        "customer_name": customer_name or "—",
        "reference_no": p.reference_no,
        "amount": p.amount,
        "note": p.note,
        "created_by": p.created_by,
        "created_at": p.created_at,
    } for p, customer_name in rows]

    return make_page(items, total, page, page_size)


@router.get("/summary")
def ledger_summary(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    customer_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    today = date.today()
    d_start = datetime.combine(date_from or today, datetime.min.time())
    d_end   = datetime.combine(date_to   or today, datetime.max.time())

    def range_sum(ttype: str):
        q = db.query(func.sum(PaymentLedger.amount)).filter(
            PaymentLedger.transaction_type == ttype,
            PaymentLedger.created_at >= d_start,
            PaymentLedger.created_at <= d_end,
            PaymentLedger.tenant_id == tenant_id,
        )
        if customer_id:
            q = q.filter(PaymentLedger.customer_id == customer_id)
        return q.scalar() or 0

    def range_count(ttype: str):
        q = db.query(func.count(PaymentLedger.id)).filter(
            PaymentLedger.transaction_type == ttype,
            PaymentLedger.created_at >= d_start,
            PaymentLedger.created_at <= d_end,
            PaymentLedger.tenant_id == tenant_id,
        )
        if customer_id:
            q = q.filter(PaymentLedger.customer_id == customer_id)
        return q.scalar() or 0

    sale_payment = round(range_sum("SALE_PAYMENT"), 2)
    due_payment  = round(range_sum("DUE_PAYMENT"), 2)
    discount     = round(abs(range_sum("DISCOUNT")), 2)
    ret          = round(abs(range_sum("RETURN")), 2)
    total_cash_in = round(sale_payment + due_payment, 2)
    net_cash      = round(total_cash_in - ret, 2)

    due_q = db.query(func.sum(Sale.due_amount)).filter(Sale.tenant_id == tenant_id)
    if customer_id:
        due_q = due_q.filter(Sale.customer_id == customer_id)
    total_due = due_q.scalar() or 0

    label = str(date_from or today)
    if date_to and date_to != (date_from or today):
        label = f"{date_from or today} → {date_to}"

    return {
        "date": label,
        "sale_payment":          sale_payment,
        "due_payment":           due_payment,
        "total_cash_in":         total_cash_in,
        "discount_given":        discount,
        "return_amount":         ret,
        "net_cash":              net_cash,
        "total_outstanding_due": round(total_due, 2),
        "counts": {
            "sale_payment": range_count("SALE_PAYMENT"),
            "due_payment":  range_count("DUE_PAYMENT"),
            "discount":     range_count("DISCOUNT"),
            "return":       range_count("RETURN"),
        }
    }


@router.get("/operator-summary")
def operator_summary(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    today = date.today()
    d_start = datetime.combine(date_from or today, datetime.min.time())
    d_end   = datetime.combine(date_to   or today, datetime.max.time())

    rows = (
        db.query(
            PaymentLedger.created_by,
            PaymentLedger.transaction_type,
            func.count(PaymentLedger.id).label("txn_count"),
            func.sum(PaymentLedger.amount).label("total"),
        )
        .filter(
            PaymentLedger.created_at >= d_start,
            PaymentLedger.created_at <= d_end,
            PaymentLedger.tenant_id == tenant_id,
        )
        .group_by(PaymentLedger.created_by, PaymentLedger.transaction_type)
        .all()
    )

    ops: dict = {}
    for created_by, ttype, cnt, total in rows:
        op = created_by or "Unknown"
        if op not in ops:
            ops[op] = {
                "operator": op,
                "sale_payment":  {"amount": 0, "count": 0},
                "due_payment":   {"amount": 0, "count": 0},
                "discount":      {"amount": 0, "count": 0},
                "return":        {"amount": 0, "count": 0},
            }
        amount = round(float(total or 0), 2)
        if ttype == "SALE_PAYMENT":
            ops[op]["sale_payment"]  = {"amount": amount,      "count": cnt}
        elif ttype == "DUE_PAYMENT":
            ops[op]["due_payment"]   = {"amount": amount,      "count": cnt}
        elif ttype == "DISCOUNT":
            ops[op]["discount"]      = {"amount": abs(amount), "count": cnt}
        elif ttype == "RETURN":
            ops[op]["return"]        = {"amount": abs(amount), "count": cnt}

    result = []
    for op_data in ops.values():
        cash_in   = round(op_data["sale_payment"]["amount"] + op_data["due_payment"]["amount"], 2)
        net_cash  = round(cash_in - op_data["return"]["amount"], 2)
        txn_total = sum(op_data[k]["count"] for k in ["sale_payment", "due_payment", "discount", "return"])
        result.append({**op_data, "total_cash_in": cash_in, "net_cash": net_cash, "total_txn": txn_total})

    result.sort(key=lambda x: x["net_cash"], reverse=True)

    label = str(date_from or today)
    if date_to and date_to != (date_from or today):
        label = f"{date_from or today} → {date_to}"

    return {
        "date": label,
        "operators": result,
        "grand": {
            "total_cash_in":  round(sum(r["total_cash_in"]     for r in result), 2),
            "discount_given": round(sum(r["discount"]["amount"] for r in result), 2),
            "return_amount":  round(sum(r["return"]["amount"]   for r in result), 2),
            "net_cash":       round(sum(r["net_cash"]           for r in result), 2),
            "total_txn":      sum(r["total_txn"] for r in result),
        }
    }
