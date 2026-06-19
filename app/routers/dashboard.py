from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date, timedelta

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.product import Product
from app.models.sales import Sale
from app.models.sales_item import SaleItem
from app.models.purchase import Purchase
from app.models.customer import Customer

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(get_current_user)]
)


@router.get("/")
def dashboard_summary(db: Session = Depends(get_db)):

    today = date.today()
    month_start = date(today.year, today.month, 1)

    # â”€â”€ KPI counts â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    total_products  = db.query(Product).count()
    total_customers = db.query(Customer).count()

    products   = db.query(Product).all()
    stock_value = sum((p.current_stock or 0) * (p.purchase_price or 0) for p in products)

    total_outstanding_due = db.query(func.coalesce(func.sum(Customer.current_due), 0)).scalar()

    # Today
    today_sales_rows = db.query(Sale).filter(Sale.created_at >= today).all()
    today_sales      = sum(s.total_amount for s in today_sales_rows)
    today_invoices   = len(today_sales_rows)

    # try to pull today's collections from payment_ledger; fallback gracefully
    today_collections = 0.0
    try:
        from app.models.payment_ledger import PaymentLedger
        today_collections = db.query(
            func.coalesce(func.sum(PaymentLedger.amount), 0)
        ).filter(
            PaymentLedger.transaction_type.in_(["SALE_PAYMENT", "DUE_PAYMENT"]),
            func.date(PaymentLedger.created_at) == today
        ).scalar()
    except Exception:
        pass

    # Month
    month_sales_rows = db.query(Sale).filter(Sale.created_at >= month_start).all()
    month_sales      = sum(s.total_amount for s in month_sales_rows)
    month_purchase   = sum(
        p.total_amount
        for p in db.query(Purchase).filter(Purchase.created_at >= month_start).all()
    )
    profit = month_sales - month_purchase

    # â”€â”€ Low stock items â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    low_stock_count = db.query(Product).filter(Product.current_stock <= 10).count()
    low_stock_items = [
        {"id": p.id, "name": p.name, "stock": p.current_stock or 0}
        for p in db.query(Product)
                   .filter(Product.current_stock <= 10)
                   .order_by(Product.current_stock)
                   .limit(8).all()
    ]

    # â”€â”€ Last 7 days sales chart â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    sales_chart = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        d_next = d + timedelta(days=1)
        day_total = db.query(func.coalesce(func.sum(Sale.total_amount), 0)).filter(
            Sale.created_at >= d, Sale.created_at < d_next
        ).scalar()
        day_count = db.query(Sale).filter(
            Sale.created_at >= d, Sale.created_at < d_next
        ).count()
        sales_chart.append({
            "date": d.isoformat(),
            "label": d.strftime("%d %b"),
            "amount": float(day_total),
            "count": day_count
        })

    # â”€â”€ Top 5 products this month by revenue â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    top_rows = (
        db.query(SaleItem.product_id,
                 func.sum(SaleItem.quantity).label("qty"),
                 func.sum(SaleItem.amount).label("revenue"))
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(Sale.created_at >= month_start)
        .group_by(SaleItem.product_id)
        .order_by(func.sum(SaleItem.amount).desc())
        .limit(5)
        .all()
    )
    top_products = []
    for r in top_rows:
        p = db.query(Product).filter(Product.id == r.product_id).first()
        top_products.append({
            "name": p.name if p else "Unknown",
            "qty": int(r.qty),
            "revenue": float(r.revenue)
        })

    # â”€â”€ Recent 6 sales â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    recent_rows = db.query(Sale).order_by(Sale.id.desc()).limit(6).all()
    recent_sales = []
    for s in recent_rows:
        cname = None
        if s.customer_id:
            c = db.query(Customer).filter(Customer.id == s.customer_id).first()
            cname = c.name if c else None
        recent_sales.append({
            "invoice_no": s.invoice_no,
            "customer_name": cname or "Walk-in",
            "total": s.total_amount,
            "due": s.due_amount,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        })

    return {
        # KPIs
        "total_products":        total_products,
        "total_customers":       total_customers,
        "stock_value":           round(stock_value, 2),
        "total_outstanding_due": round(float(total_outstanding_due), 2),
        "today_sales":           round(today_sales, 2),
        "today_invoices":        today_invoices,
        "today_collections":     round(float(today_collections), 2),
        "month_sales":           round(month_sales, 2),
        "total_purchase":        round(month_purchase, 2),
        "profit":                round(profit, 2),
        "low_stock":             low_stock_count,
        # Detail data
        "sales_chart":           sales_chart,
        "top_products":          top_products,
        "low_stock_items":       low_stock_items,
        "recent_sales":          recent_sales,
    }
