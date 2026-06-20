import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine, SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.models.category import Category
from app.models.sale_return import SaleReturn, SaleReturnItem
from app.models.product_waste import ProductWaste
from app.models.stock_transaction import StockTransaction
from app.models.customer_payment import CustomerPayment
from app.models.payment_ledger import PaymentLedger

from app.routers.auth import router as auth_router
from app.routers.category import router as category_router
from app.routers.product import router as product_router
from app.routers.supplier import router as supplier_router
from app.routers.purchase import router as purchase_router
from app.routers.customer import router as customer_router
from app.routers.sales import router as sales_router
from app.routers.dashboard import router as dashboard_router
from app.routers.reports import router as reports_router
from app.routers.sale_return import router as sale_return_router
from app.routers.product_waste import router as product_waste_router
from app.routers.stock_transaction import router as stock_transaction_router
from app.routers.customer_payment import router as customer_payment_router
from app.routers.payment_ledger import router as payment_ledger_router

Base.metadata.create_all(bind=engine)


def run_migrations():
    """Add new columns to existing tables without dropping data."""
    with engine.connect() as conn:
        migrations = [
            "ALTER TABLE sales ADD COLUMN discount_amount FLOAT DEFAULT 0",
            "ALTER TABLE customer_payments ADD COLUMN sale_id INT",
            "ALTER TABLE customer_payments ADD COLUMN discount_amount FLOAT DEFAULT 0",
            "ALTER TABLE customer_payments ADD COLUMN amount FLOAT DEFAULT 0",
            "ALTER TABLE products ADD COLUMN mrp FLOAT DEFAULT 0",
        ]
        for sql in migrations:
            try:
                conn.execute(__import__('sqlalchemy').text(sql))
                conn.commit()
            except Exception:
                pass  # column already exists


run_migrations()


def seed_default_user():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "systemadmin@gmail.com").first()
        if user is None:
            db.add(User(
                username="systemadmin@gmail.com",
                password=hash_password("admin@123##"),
                role="system_admin"
            ))
            db.commit()
        elif not user.password.startswith("$2b$"):
            user.password = hash_password("admin@123##")
            db.commit()
    finally:
        db.close()


seed_default_user()

app = FastAPI(title="Inventory API")

origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:4200").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(category_router)
app.include_router(product_router)
app.include_router(supplier_router)
app.include_router(purchase_router)
app.include_router(customer_router)
app.include_router(sales_router)
app.include_router(dashboard_router)
app.include_router(reports_router)
app.include_router(sale_return_router)
app.include_router(product_waste_router)
app.include_router(stock_transaction_router)
app.include_router(customer_payment_router)
app.include_router(payment_ledger_router)


@app.get("/")
def root():
    return {"message": "Inventory API Running"}
