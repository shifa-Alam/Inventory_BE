from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_
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


def _pct_change(current, previous):
    if not previous:
        return None
    return round((current - previous) / previous * 100, 1)


@router.get("/")
def dashboard_summary(db: Session = Depends(get_db)):

    today        = date.today()
    yesterday    = today - timedelta(days=1)
    month_start  = date(today.year, today.month, 1)
    week_ago     = today - timedelta(days=6)

    first_of_month   = date(today.year, today.month, 1)
    last_month_end   = first_of_month - timedelta(days=1)
    last_month_start = date(last_month_end.year, last_month_end.month, 1)

    dt_today_min   = datetime.combine(today, time.min)
    dt_today_max   = datetime.combine(today, time.max)
    dt_yest_min    = datetime.combine(yesterday, time.min)
    dt_yest_max    = datetime.combine(yesterday, time.max)
    dt_month_min   = datetime.combine(month_start, time.min)
    dt_lm_min      = datetime.combine(last_month_start, time.min)
    dt_lm_max      = datetime.combine(last_month_end, time.max)
    dt_week_min    = datetime.combine(week_ago, time.min)

    # ── 1. Sales aggregates (today / yesterday / month / last month) ──
    # Single query using conditional aggregation
    sale_aggs = db.query(
        func.coalesce(func.sum(case(
            (and_(Sale.created_at >= dt_today_min, Sale.created_at <= dt_today_max), Sale.total_amount),
            else_=0
        )), 0).label("today_sales"),
        func.coalesce(func.count(case(
            (and_(Sale.created_at >= dt_today_min, Sale.created_at <= dt_today_max), Sale.id),
            else_=None
        )), 0).label("today_invoices"),
        func.coalesce(func.sum(case(
            (and_(Sale.created_at >= dt_yest_min, Sale.created_at <= dt_yest_max), Sale.total_amount),
            else_=0
        )), 0).label("yesterday_sales"),
        func.coalesce(func.sum(case(
            (and_(Sale.created_at >= dt_month_min, Sale.created_at <= dt_today_max), Sale.total_amount),
            else_=0
        )), 0).label("month_sales"),
        func.coalesce(func.count(case(
            (and_(Sale.created_at >= dt_month_min, Sale.created_at <= dt_today_max), Sale.id),
            else_=None
        )), 0).label("month_invoices"),
        func.coalesce(func.sum(case(
            (and_(Sale.created_at >= dt_lm_min, Sale.created_at <= dt_lm_max), Sale.total_amount),
            else_=0
        )), 0).label("last_month_sales"),
    ).one()

    today_sales      = float(sale_aggs.today_sales)
    today_invoices   = int(sale_aggs.today_invoices)
    yesterday_sales  = float(sale_aggs.yesterday_sales)
    month_sales      = float(sale_aggs.month_sales)
    month_invoices   = int(sale_aggs.month_invoices)
    last_month_sales = float(sale_aggs.last_month_sales)

    # ── 2. Payment aggregates (today / month) ─────────────────────
    pay_types = ["SALE_PAYMENT", "DUE_PAYMENT"]
    pay_aggs = db.query(
        func.coalesce(func.sum(case(
            (and_(PaymentLedger.created_at >= dt_today_min,
                  PaymentLedger.created_at <= dt_today_max,
                  PaymentLedger.transaction_type.in_(pay_types)), PaymentLedger.amount),
            else_=0
        )), 0).label("today_collections"),
        func.coalesce(func.sum(case(
            (and_(PaymentLedger.created_at >= dt_month_min,
                  PaymentLedger.transaction_type.in_(pay_types)), PaymentLedger.amount),
            else_=0
        )), 0).label("month_collections"),
    ).one()

    today_collections = float(pay_aggs.today_collections)
    month_collections = float(pay_aggs.month_collections)

    # ── 3. Purchase total this month ──────────────────────────────
    month_purchase = float(db.query(
        func.coalesce(func.sum(Purchase.total_amount), 0)
    ).filter(Purchase.created_at >= dt_month_min).scalar())

    # ── 4. Inventory aggregates ───────────────────────────────────
    inv_aggs = db.query(
        func.count(Product.id).label("total_products"),
        func.coalesce(func.sum(Product.current_stock * Product.purchase_price), 0).label("stock_value"),
        func.coalesce(func.sum(case((Product.current_stock <= 10, 1), else_=0)), 0).label("low_stock_count"),
    ).one()

    total_products  = int(inv_aggs.total_products)
    stock_value     = float(inv_aggs.stock_value)
    low_stock_count = int(inv_aggs.low_stock_count)

    total_customers = db.query(func.count(Customer.id)).scalar()
    total_outstanding_due = float(db.query(func.coalesce(func.sum(Customer.current_due), 0)).scalar())

    # ── 5. 7-day chart — 2 queries instead of 21 ─────────────────
    chart_sales_rows = db.query(
        func.date(Sale.created_at).label("day"),
        func.coalesce(func.sum(Sale.total_amount), 0).label("amount"),
        func.count(Sale.id).label("count"),
    ).filter(Sale.created_at >= dt_week_min).group_by(func.date(Sale.created_at)).all()

    chart_pay_rows = db.query(
        func.date(PaymentLedger.created_at).label("day"),
        func.coalesce(func.sum(PaymentLedger.amount), 0).label("amount"),
    ).filter(
        PaymentLedger.created_at >= dt_week_min,
        PaymentLedger.transaction_type.in_(pay_types),
    ).group_by(func.date(PaymentLedger.created_at)).all()

    sales_by_day   = {str(r.day): (float(r.amount), int(r.count)) for r in chart_sales_rows}
    collect_by_day = {str(r.day): float(r.amount) for r in chart_pay_rows}

    sales_chart = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        key = d.isoformat()
        amt, cnt = sales_by_day.get(key, (0.0, 0))
        sales_chart.append({
            "date":       key,
            "label":      d.strftime("%d %b"),
            "amount":     amt,
            "collection": collect_by_day.get(key, 0.0),
            "count":      cnt,
        })

    # ── 6. Top 5 products by revenue this month ───────────────────
    top_rows = (
        db.query(
            SaleItem.product_id,
            Product.name.label("product_name"),
            Product.purchase_price.label("purchase_price"),
            func.sum(SaleItem.quantity).label("qty"),
            func.sum(SaleItem.amount).label("revenue"),
        )
        .join(Sale, Sale.id == SaleItem.sale_id)
        .join(Product, Product.id == SaleItem.product_id)
        .filter(Sale.created_at >= dt_month_min)
        .group_by(SaleItem.product_id, Product.name, Product.purchase_price)
        .order_by(func.sum(SaleItem.amount).desc())
        .limit(5).all()
    )
    top_products = []
    for r in top_rows:
        revenue = float(r.revenue)
        cost    = (r.purchase_price or 0) * float(r.qty)
        margin  = round((revenue - cost) / revenue * 100, 1) if revenue else 0
        top_products.append({
            "name":    r.product_name,
            "qty":     int(r.qty),
            "revenue": revenue,
            "margin":  margin,
        })

    # ── 7. Slow-moving items ──────────────────────────────────────
    # Products with stock > 0, sold least this month
    slow_rows = (
        db.query(
            Product.id,
            Product.name,
            Product.current_stock,
            func.coalesce(func.sum(SaleItem.quantity), 0).label("month_qty"),
        )
        .outerjoin(
            SaleItem,
            and_(SaleItem.product_id == Product.id,
                 SaleItem.sale_id.in_(
                     db.query(Sale.id).filter(Sale.created_at >= dt_month_min).scalar_subquery()
                 ))
        )
        .filter(Product.current_stock > 0)
        .group_by(Product.id, Product.name, Product.current_stock)
        .order_by(func.coalesce(func.sum(SaleItem.quantity), 0).asc(), Product.current_stock.desc())
        .limit(8).all()
    )
    slow_moving_items = [
        {"name": r.name, "stock": r.current_stock or 0, "month_qty": int(r.month_qty)}
        for r in slow_rows
    ]

    # ── 8. Low stock items ────────────────────────────────────────
    low_stock_items = [
        {
            "id":        p.id,
            "name":      p.name,
            "stock":     p.current_stock or 0,
            "max_stock": max((p.current_stock or 0) + 50, 50),
        }
        for p in db.query(Product)
                   .filter(Product.current_stock <= 10)
                   .order_by(Product.current_stock)
                   .limit(8).all()
    ]

    # ── 9. Top due customers ──────────────────────────────────────
    top_due_customers = [
        {"name": c.name, "phone": c.phone, "due": round(c.current_due, 2)}
        for c in db.query(Customer)
                   .filter(Customer.current_due > 0)
                   .order_by(Customer.current_due.desc())
                   .limit(5).all()
    ]

    # ── 10. Recent 8 sales — single join query ────────────────────
    recent_rows = (
        db.query(Sale, Customer.name.label("customer_name"))
        .outerjoin(Customer, Customer.id == Sale.customer_id)
        .order_by(Sale.id.desc())
        .limit(8).all()
    )
    recent_sales = [
        {
            "invoice_no":    s.invoice_no,
            "customer_name": cname or "Walk-in",
            "total":         s.total_amount,
            "paid":          s.paid_amount,
            "due":           s.due_amount,
            "created_at":    s.created_at.isoformat() if s.created_at else None,
        }
        for s, cname in recent_rows
    ]

    # ── Derived metrics ───────────────────────────────────────────
    profit         = month_sales - month_purchase
    profit_margin  = round(profit / month_sales * 100, 1) if month_sales else 0
    avg_order_value = round(month_sales / month_invoices, 2) if month_invoices else 0
    collection_rate = round(month_collections / month_sales * 100, 1) if month_sales else 0

    return {
        "today_sales":           round(today_sales, 2),
        "today_invoices":        today_invoices,
        "today_collections":     round(today_collections, 2),
        "today_trend":           _pct_change(today_sales, yesterday_sales),
        "yesterday_sales":       round(yesterday_sales, 2),
        "month_sales":           round(month_sales, 2),
        "month_invoices":        month_invoices,
        "month_trend":           _pct_change(month_sales, last_month_sales),
        "last_month_sales":      round(last_month_sales, 2),
        "total_purchase":        round(month_purchase, 2),
        "profit":                round(profit, 2),
        "profit_margin":         profit_margin,
        "avg_order_value":       avg_order_value,
        "collection_rate":       collection_rate,
        "month_collections":     round(month_collections, 2),
        "total_products":        total_products,
        "total_customers":       total_customers,
        "stock_value":           round(stock_value, 2),
        "total_outstanding_due": round(total_outstanding_due, 2),
        "low_stock":             low_stock_count,
        "sales_chart":           sales_chart,
        "top_products":          top_products,
        "top_due_customers":     top_due_customers,
        "low_stock_items":       low_stock_items,
        "slow_moving_items":     slow_moving_items,
        "recent_sales":          recent_sales,
    }
