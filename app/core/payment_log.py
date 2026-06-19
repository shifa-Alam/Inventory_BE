from sqlalchemy.orm import Session
from app.models.payment_ledger import PaymentLedger


def log_payment(
    db: Session,
    transaction_type: str,
    amount: float,
    reference_no: str,
    sale_id: int | None = None,
    customer_id: int | None = None,
    note: str | None = None,
    created_by: str | None = None,
):
    entry = PaymentLedger(
        transaction_type=transaction_type,
        sale_id=sale_id,
        customer_id=customer_id,
        reference_no=reference_no,
        amount=round(amount, 2),
        note=note,
        created_by=created_by,
    )
    db.add(entry)
