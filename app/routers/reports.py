from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date

from app.core.database import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.core.pagination import make_page
from app.models.product import Product
from app.models.category import Category
from app.models.sales import Sale
from app.models.sales_item import SaleItem
from app.models.customer import Customer

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
    dependencies=[Depends(get_current_user)]
)


@router.get("/stock/summary")
def stock_summary(db: Session = Depends(get_db), tenant_id: int = Depends(get_tenant_id)):
    products = db.query(Product).filter(Product.tenant_id == tenant_id).all()
    total_products  = len(products)
    total_value     = sum((p.current_stock or 0) * (p.purchase_price or 0) for p in products)
    low_stock_count = sum(1 for p in products if 0 < (p.current_stock or 0) <= 10)
    out_of_stock    = sum(1 for p in products if (p.current_stock or 0) == 0)
    return {
        "total_products": total_products,
        "total_stock_value": total_value,
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock,
    }


@router.get("/stock")
def stock_report(
    category_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    query = db.query(Product, Category.name.label("category_name")).outerjoin(
        Category, Product.category_id == Category.id
    ).filter(Product.tenant_id == tenant_id)

    if category_id:
        query = query.filter(Product.category_id == category_id)
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%") | Product.sku.ilike(f"%{search}%"))

    products_all = query.all()

    def get_status(stock):
        if stock == 0: return "OUT"
        if stock <= 10: return "LOW"
        return "OK"

    if status == "LOW":
        products_all = [(p, cn) for p, cn in products_all if 0 < (p.current_stock or 0) <= 10]
    elif status == "OUT":
        products_all = [(p, cn) for p, cn in products_all if (p.current_stock or 0) == 0]
    elif status == "OK":
        products_all = [(p, cn) for p, cn in products_all if (p.current_stock or 0) > 10]

    total = len(products_all)
    page_data = products_all[(page - 1) * page_size: page * page_size]

    result = [
        {
            "id": p.id, "name": p.name, "sku": p.sku,
            "category": cat_name or "—",
            "current_stock": p.current_stock or 0,
            "purchase_price": p.purchase_price or 0,
            "sale_price": p.sale_price or 0,
            "stock_value": (p.current_stock or 0) * (p.purchase_price or 0),
            "status": get_status(p.current_stock or 0),
        }
        for p, cat_name in page_data
    ]
    return make_page(result, total, page, page_size)


@router.get("/low-stock")
def low_stock(
    threshold: int = Query(10, ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    query = db.query(Product).filter(Product.current_stock <= threshold, Product.tenant_id == tenant_id)
    total = query.count()
    products = query.offset((page - 1) * page_size).limit(page_size).all()
    return make_page([{"name": p.name, "sku": p.sku, "stock": p.current_stock} for p in products], total, page, page_size)


@router.get("/sales/daily")
def daily_sales(db: Session = Depends(get_db), tenant_id: int = Depends(get_tenant_id)):
    today = date.today()
    sales = db.query(Sale).filter(func.date(Sale.created_at) == today, Sale.tenant_id == tenant_id).all()
    return [{"id": s.id, "total": s.total_amount, "paid": s.paid_amount, "due": s.due_amount, "date": s.created_at} for s in sales]


@router.get("/profit")
def profit_report(db: Session = Depends(get_db), tenant_id: int = Depends(get_tenant_id)):
    sale_items = db.query(SaleItem).filter(SaleItem.tenant_id == tenant_id).all()
    total_profit = 0
    for item in sale_items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            total_profit += (item.rate - product.purchase_price) * item.quantity
    return {"total_profit": total_profit}


@router.get("/customers/due")
def customer_due(
    min_due: Optional[float] = Query(None, ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    query = db.query(Customer).filter(Customer.current_due > 0, Customer.tenant_id == tenant_id)
    if min_due is not None:
        query = query.filter(Customer.current_due >= min_due)
    total = query.count()
    customers = query.offset((page - 1) * page_size).limit(page_size).all()
    return make_page([{"name": c.name, "phone": c.phone, "due": c.current_due} for c in customers], total, page, page_size)
