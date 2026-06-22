from sqlalchemy.orm import Session
from app.models.stock_transaction import StockTransaction
from app.models.product import Product


def log_stock(
    db: Session,
    product: Product,
    transaction_type: str,
    quantity: float,
    reference_id: int,
    reference_no: str,
    tenant_id: int,
    note: str = ""
):
    stock_before = product.current_stock

    if transaction_type in ("PURCHASE", "RETURN"):
        product.current_stock += quantity
    else:  # SALE, WASTE
        product.current_stock -= quantity

    db.add(StockTransaction(
        product_id=product.id,
        transaction_type=transaction_type,
        reference_id=reference_id,
        reference_no=reference_no,
        quantity=quantity,
        stock_before=stock_before,
        stock_after=product.current_stock,
        note=note,
        tenant_id=tenant_id,
    ))
