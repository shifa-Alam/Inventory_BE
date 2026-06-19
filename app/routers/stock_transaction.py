from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from datetime import datetime, date, time

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.pagination import make_page
from app.models.stock_transaction import StockTransaction
from app.models.product import Product

router = APIRouter(
    prefix="/stock-transactions",
    tags=["Stock Transactions"],
    dependencies=[Depends(get_current_user)]
)


@router.get("/")
def get_transactions(
    product_id: Optional[int] = Query(None),
    transaction_type: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    query = db.query(StockTransaction).order_by(desc(StockTransaction.id))

    if product_id:
        query = query.filter(StockTransaction.product_id == product_id)
    if transaction_type:
        query = query.filter(StockTransaction.transaction_type == transaction_type.upper())
    if date_from:
        query = query.filter(StockTransaction.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        query = query.filter(StockTransaction.created_at <= datetime.combine(date_to, time.max))

    total = query.count()
    transactions = query.offset((page - 1) * page_size).limit(page_size).all()

    result = []
    for t in transactions:
        product = db.query(Product).filter(Product.id == t.product_id).first()
        result.append({
            "id": t.id,
            "product_id": t.product_id,
            "product_name": product.name if product else None,
            "transaction_type": t.transaction_type,
            "reference_no": t.reference_no,
            "quantity": t.quantity,
            "stock_before": t.stock_before,
            "stock_after": t.stock_after,
            "note": t.note,
            "created_at": t.created_at
        })

    return make_page(result, total, page, page_size)


@router.get("/product/{product_id}")
def get_product_ledger(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()

    transactions = (
        db.query(StockTransaction)
        .filter(StockTransaction.product_id == product_id)
        .order_by(StockTransaction.id)
        .all()
    )

    return {
        "product_id": product_id,
        "product_name": product.name if product else None,
        "current_stock": product.current_stock if product else None,
        "ledger": [
            {
                "id": t.id,
                "type": t.transaction_type,
                "reference_no": t.reference_no,
                "quantity": t.quantity,
                "stock_before": t.stock_before,
                "stock_after": t.stock_after,
                "note": t.note,
                "date": t.created_at
            }
            for t in transactions
        ]
    }
