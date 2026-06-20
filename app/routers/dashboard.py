from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date, timedelta, time

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.product import Product
from app.models.sales import Sale
from app.models.sales_item import SaleItem
from app.models.purchase import Purchase
from app.models.customer import Customer
from app.models.payment_ledger import PaymentLedger

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(get_current_user)]
)


def _sales_in_range(db, dt_from, dt_to):
    rows = db.query(Sale).filter(Sale.created_at >= dt_from, Sale.created_at <= dt_to).all()
    return rows


def _sum_sales(rows):
    return sum(s.total_amount for s in rows)


def _pct_change(current, previous):
    if previous == 0:
        return None
    return round((current - previous) / previous * 100, 1)


@router.get("/")
def dashboard_summary(db: Session = Depends(get_db)):

    today      = date.today()
    yesterday  = today - timedelta(days=1)
    month_start = date(today.year, today.month, 1)

    # last month range
    first_of_month = date(today.year, today.month, 1)
    last_month_end = first_of_month - timedelta(days=1)
    last_month_start = date(last_month_end.year, last_month_end.month, 1)

    # ── Today / Yesterday ────────────────────────────────────────
    today_rows     = _sales_in_range(db, datetime.combine(today, time.min), datetime.combine(today, time.max))
    yesterday_rows = _sales_in_range(db, datetime.combine(yesterday, time.min), datetime.combine(yesterday, time.max))

    today_sales    = _sum_sales(today_rows)
    yesterday_sales = _sum_sales(yesterday_rows)
    today_invoices = len(today_rows)

    today_trend    = _pct_change(today_sales, yesterday_sales)

    # ── Collections ──────────────────────────────────────────────
    today_collections = db.query(
        func.coalesce(func.sum(PaymentLedger.amount), 0)
    ).filter(
        PaymentLedger.transaction_type.in_(["SALE_PAYMENT", "DUE_PAYMENT"]),
        PaymentLedger.created_at >= datetime.combine(today, time.min),
        PaymentLedger.created_at <= datetime.combine(today, time.max),
    ).scalar()

    month_collections = db.query(
        func.coalesce(func.sum(PaymentLedger.amount), 0)
    ).filter(
        PaymentLedger.transaction_type.in_(["SALE_PAYMENT", "DUE_PAYMENT"]),
        PaymentLedger.created_at >= datetime.combine(month_start, time.min),
    ).scalar()

    # ── Month vs Last Month ───────────────────────────────────────
    month_rows      = _sales_in_range(db, datetime.combine(month_start, time.min), datetime.combine(today, time.max))
    last_month_rows = _sales_in_range(db, datetime.combine(last_month_start, time.min), datetime.combine(last_month_end, time.max))

    month_sales      = _sum_sales(month_rows)
    last_month_sales = _sum_sales(last_month_rows)
    month_invoices   = len(month_rows)
    month_trend      = _pct_change(month_sales, last_month_sales)

    month_purchase = sum(
        p.total_amount
        for p in db.query(Purchase).filter(Purchase.created_at >= datetime.combine(month_start, time.min)).all()
    )
    profit      = month_sales - month_purchase
    profit_margin = round(profit / month_sales * 100, 1) if month_sales else 0

    # avg order value
    avg_order_value = round(month_sales / month_invoices, 2) if month_invoices else 0

    # collection rate this month
    collection_rate = round(month_collections / month_sales * 100, 1) if month_sales else 0

    # ── Inventory ────────────────────────────────────────────────
    total_products  = db.query(Product).count()
    total_customers = db.query(Customer).count()
    products        = db.query(Product).all()
    stock_value     = sum((p.current_stock or 0) * (p.purchase_price or 0) for p in products)
    total_outstanding_due = db.query(func.coalesce(func.sum(Customer.current_due), 0)).scalar()

    # ── Low stock ────────────────────────────────────────────────
    low_stock_count = db.query(Product).filter(Product.current_stock <= 10).count()
    low_stock_items = [
        {
            "id": p.id, "name": p.name,
            "stock": p.current_stock or 0,
            "max_stock": max((p.current_stock or 0) + 50, 50),
        }
        for p in db.query(Product)
                   .filter(Product.current_stock <= 10)
                   .order_by(Product.current_stock)
                   .limit(8).all()
    ]

    # ── Top 5 customers by outstanding due ───────────────────────
    top_due_customers = [
        {"name": c.name, "phone": c.phone, "due": round(c.current_due, 2)}
        for c in db.query(Customer)
                   .filter(Customer.current_due > 0)
                   .order_by(Customer.current_due.desc())
                   .limit(5).all()
    ]

    # ── 7-day sales chart ─────────────────────────────────────────
    sales_chart = []
    for i in range(6, -1, -1):
        d      = today - timedelta(days=i)
        d_next = d + timedelta(days=1)
        day_total = db.query(func.coalesce(func.sum(Sale.total_amount), 0)).filter(
            Sale.created_at >= d, Sale.created_at < d_next
        ).scalar()
        day_collect = db.query(func.coalesce(func.sum(PaymentLedger.amount), 0)).filter(
            PaymentLedger.transaction_type.in_(["SALE_PAYMENT", "DUE_PAYMENT"]),
            PaymentLedger.created_at >= d,
            PaymentLedger.created_at < d_next,
        ).scalar()
        day_count = db.query(Sale).filter(Sale.created_at >= d, Sale.created_at < d_next).count()
        sales_chart.append({
            "date":        d.isoformat(),
            "label":       d.strftime("%d %b"),
            "amount":      float(day_total),
            "collection":  float(day_collect),
            "count":       day_count,
        })

    # ── Top 5 products by revenue this month ─────────────────────
    top_rows = (
        db.query(SaleItem.product_id,
                 func.sum(SaleItem.quantity).label("qty"),
                 func.sum(SaleItem.amount).label("revenue"))
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(Sale.created_at >= datetime.combine(month_start, time.min))
        .group_by(SaleItem.product_id)
        .order_by(func.sum(SaleItem.amount).desc())
        .limit(5).all()
    )
    top_products = []
    for r in top_rows:
        p = db.query(Product).filter(Product.id == r.product_id).first()
        cost = (p.purchase_price or 0) * r.qty if p else 0
        margin = round((float(r.revenue) - cost) / float(r.revenue) * 100, 1) if r.revenue else 0
        top_products.append({
            "name":    p.name if p else "Unknown",
            "qty":     int(r.qty),
            "revenue": float(r.revenue),
            "margin":  margin,
        })

    # ── Slow-moving items (in stock but least sold this month) ───────
    sold_ids_this_month = {r.product_id for r in top_rows}
    slow_moving_items = []
    # Products with stock > 0, ordered by qty sold this month ascending (unsold first)
    slow_rows = (
        db.query(SaleItem.product_id,
                 func.coalesce(func.sum(SaleItem.quantity), 0).label("qty"))
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(Sale.created_at >= datetime.combine(month_start, time.min))
        .group_by(SaleItem.product_id)
        .order_by(func.sum(SaleItem.quantity).asc())
        .all()
    )
    slow_sold_map = {r.product_id: int(r.qty) for r in slow_rows}

    # Products with stock > 0 not sold at all this month
    unsold = (
        db.query(Product)
        .filter(Product.current_stock > 0, ~Product.id.in_(slow_sold_map.keys()))
        .order_by(Product.current_stock.desc())
        .limit(5).all()
    )
    for p in unsold:
        slow_moving_items.append({
            "name": p.name, "stock": p.current_stock or 0, "month_qty": 0
        })

    # Products sold very little this month (fill up to 8 total)
    if len(slow_moving_items) < 8:
        for pid, qty in sorted(slow_sold_map.items(), key=lambda x: x[1]):
            if len(slow_moving_items) >= 8:
                break
            p = db.query(Product).filter(Product.id == pid, Product.current_stock > 0).first()
            if p:
                slow_moving_items.append({
                    "name": p.name, "stock": p.current_stock or 0, "month_qty": qty
                })

    slow_moving_items = slow_moving_items[:8]

    # ── Recent 8 sales ────────────────────────────────────────────
    recent_rows  = db.query(Sale).order_by(Sale.id.desc()).limit(8).all()
    recent_sales = []
    for s in recent_rows:
        cname = None
        if s.customer_id:
            c = db.query(Customer).filter(Customer.id == s.customer_id).first()
            cname = c.name if c else None
        recent_sales.append({
            "invoice_no":   s.invoice_no,
            "customer_name": cname or "Walk-in",
            "total":        s.total_amount,
            "paid":         s.paid_amount,
            "due":          s.due_amount,
            "created_at":   s.created_at.isoformat() if s.created_at else None,
        })

    return {
        # Today KPIs
        "today_sales":           round(today_sales, 2),
        "today_invoices":        today_invoices,
        "today_collections":     round(float(today_collections), 2),
        "today_trend":           today_trend,
        "yesterday_sales":       round(yesterday_sales, 2),
        # Month KPIs
        "month_sales":           round(month_sales, 2),
        "month_invoices":        month_invoices,
        "month_trend":           month_trend,
        "last_month_sales":      round(last_month_sales, 2),
        "total_purchase":        round(month_purchase, 2),
        "profit":                round(profit, 2),
        "profit_margin":         profit_margin,
        "avg_order_value":       avg_order_value,
        "collection_rate":       collection_rate,
        "month_collections":     round(float(month_collections), 2),
        # Inventory
        "total_products":        total_products,
        "total_customers":       total_customers,
        "stock_value":           round(stock_value, 2),
        "total_outstanding_due": round(float(total_outstanding_due), 2),
        "low_stock":             low_stock_count,
        # Detail data
        "sales_chart":           sales_chart,
        "top_products":          top_products,
        "top_due_customers":     top_due_customers,
        "low_stock_items":       low_stock_items,
        "slow_moving_items":     slow_moving_items,
        "recent_sales":          recent_sales,
    }
