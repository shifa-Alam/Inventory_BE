"""
Reset DB (keep systemadmin) then seed realistic dummy data.
Run: python -m scripts.reset_and_seed
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.core.stock import log_stock
from app.core.payment_log import log_payment
from app.models.user import User
from app.models.category import Category
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.customer import Customer
from app.models.purchase import Purchase
from app.models.purchase_item import PurchaseItem
from app.models.sales import Sale
from app.models.sales_item import SaleItem
from app.models.customer_payment import CustomerPayment
from app.models.payment_ledger import PaymentLedger
from app.models.stock_transaction import StockTransaction
from app.models.product_waste import ProductWaste
from app.models.sale_return import SaleReturn, SaleReturnItem
from datetime import datetime, timedelta
import random

db = SessionLocal()

# â”€â”€ 1. DELETE ALL DATA (keep systemadmin) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("Deleting existing dataâ€¦")
db.query(SaleReturnItem).delete()
db.query(SaleReturn).delete()
db.query(ProductWaste).delete()
db.query(PaymentLedger).delete()
db.query(CustomerPayment).delete()
db.query(SaleItem).delete()
db.query(Sale).delete()
db.query(PurchaseItem).delete()
db.query(Purchase).delete()
db.query(StockTransaction).delete()
db.query(Product).delete()
db.query(Category).delete()
db.query(Customer).delete()
db.query(Supplier).delete()
db.query(User).filter(User.role != "system_admin").delete()
db.commit()
print("  âœ“ All data cleared (systemadmin kept)")

# â”€â”€ 2. CATEGORIES â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("Seeding categoriesâ€¦")
cats_data = [
    ("Beverages",      "Cold drinks, juices, water"),
    ("Snacks",         "Chips, biscuits, crackers"),
    ("Dairy",          "Milk, cheese, yogurt, butter"),
    ("Grains & Rice",  "Rice, flour, wheat"),
    ("Oils & Fats",    "Cooking oil, ghee"),
    ("Spices",         "Masala, pepper, turmeric"),
    ("Personal Care",  "Soap, shampoo, toothpaste"),
    ("Cleaning",       "Detergent, dishwash, floor cleaner"),
]
categories = []
for name, desc in cats_data:
    c = Category(name=name, description=desc)
    db.add(c)
    categories.append(c)
db.flush()
print(f"  âœ“ {len(categories)} categories")

# â”€â”€ 3. SUPPLIERS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("Seeding suppliersâ€¦")
suppliers_data = [
    ("Rahman Traders",     "01711-000001", "Mirpur, Dhaka"),
    ("Hasan Brothers",     "01811-000002", "Gulshan, Dhaka"),
    ("Karim Wholesale",    "01611-000003", "Chittagong"),
    ("Noor Distributors",  "01911-000004", "Sylhet"),
    ("Al-Amin Suppliers",  "01511-000005", "Rajshahi"),
]
suppliers = []
for name, phone, address in suppliers_data:
    s = Supplier(name=name, phone=phone, address=address)
    db.add(s)
    suppliers.append(s)
db.flush()
print(f"  âœ“ {len(suppliers)} suppliers")

# â”€â”€ 4. CUSTOMERS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("Seeding customersâ€¦")
customers_data = [
    ("Rahim Store",       "01700-111001", "Dhanmondi, Dhaka",  50000),
    ("Kamal Mini Mart",   "01800-111002", "Mohammadpur, Dhaka", 30000),
    ("Sultana Grocery",   "01600-111003", "Uttara, Dhaka",      20000),
    ("Bhai Bhai Shop",    "01900-111004", "Narayanganj",        40000),
    ("City Convenience",  "01500-111005", "Motijheel, Dhaka",   60000),
    ("Green Basket",      "01700-111006", "Wari, Dhaka",        25000),
    ("Family Store",      "01800-111007", "Khilgaon, Dhaka",    35000),
    ("Quick Mart",        "01600-111008", "Banani, Dhaka",      45000),
]
customers = []
for name, phone, address, credit in customers_data:
    c = Customer(name=name, phone=phone, address=address, credit_limit=credit, current_due=0)
    db.add(c)
    customers.append(c)
db.flush()
print(f"  âœ“ {len(customers)} customers")

# â”€â”€ 5. PRODUCTS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("Seeding productsâ€¦")
products_data = [
    # (name, sku, cat_index, purchase_price, sale_price)
    ("Coca-Cola 500ml",       "BEV-001", 0, 30,  40),
    ("7Up 1L",                "BEV-002", 0, 45,  60),
    ("Mango Juice 250ml",     "BEV-003", 0, 18,  25),
    ("Mineral Water 1.5L",    "BEV-004", 0, 12,  18),
    ("Pran Chips",            "SNK-001", 1, 10,  15),
    ("Crackers Biscuit",      "SNK-002", 1, 22,  30),
    ("Chocolate Bar",         "SNK-003", 1, 35,  50),
    ("Glucose Biscuit",       "SNK-004", 1, 18,  25),
    ("Full Cream Milk 1L",    "DAI-001", 2, 65,  85),
    ("Cheddar Cheese 200g",   "DAI-002", 2, 110, 145),
    ("Plain Yogurt 500g",     "DAI-003", 2, 50,  70),
    ("Butter 200g",           "DAI-004", 2, 90,  120),
    ("Minket Rice 5kg",       "GRN-001", 3, 280, 350),
    ("All Purpose Flour 2kg", "GRN-002", 3, 85,  110),
    ("Atta Flour 5kg",        "GRN-003", 3, 180, 230),
    ("Soybean Oil 5L",        "OIL-001", 4, 580, 700),
    ("Mustard Oil 1L",        "OIL-002", 4, 145, 185),
    ("Palm Oil 2L",           "OIL-003", 4, 165, 210),
    ("Turmeric Powder 100g",  "SPC-001", 5, 28,  40),
    ("Cumin Powder 100g",     "SPC-002", 5, 35,  50),
    ("Chili Powder 100g",     "SPC-003", 5, 30,  45),
    ("Mixed Masala 200g",     "SPC-004", 5, 55,  75),
    ("Lifebuoy Soap",         "PRC-001", 6, 22,  30),
    ("Sunsilk Shampoo 200ml", "PRC-002", 6, 85,  115),
    ("Colgate Toothpaste",    "PRC-003", 6, 60,  80),
    ("Surf Excel 500g",       "CLN-001", 7, 60,  80),
    ("Vim Dishwash 500ml",    "CLN-002", 7, 45,  60),
    ("Dettol Floor Cleaner",  "CLN-003", 7, 75,  100),
]
products = []
for name, sku, cat_idx, pp, sp in products_data:
    p = Product(
        name=name, sku=sku,
        category_id=categories[cat_idx].id,
        purchase_price=pp, sale_price=sp,
        current_stock=0
    )
    db.add(p)
    products.append(p)
db.flush()
print(f"  âœ“ {len(products)} products")

# â”€â”€ 6. PURCHASES (stock in) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("Seeding purchasesâ€¦")

def make_purchase(supplier, items_data, days_ago=0):
    dt = datetime.now() - timedelta(days=days_ago)
    pur = Purchase(supplier_id=supplier.id, total_amount=0, invoice_no="", created_at=dt)
    db.add(pur)
    db.flush()
    date_part = dt.strftime("%Y%m%d")
    pur.invoice_no = f"PUR-{date_part}-{str(pur.id).zfill(5)}"
    total = 0
    for product, qty, rate in items_data:
        amt = qty * rate
        total += amt
        db.add(PurchaseItem(purchase_id=pur.id, product_id=product.id, quantity=qty, rate=rate, amount=amt))
        log_stock(db=db, product=product, transaction_type="PURCHASE",
                  quantity=qty, reference_id=pur.id, reference_no=pur.invoice_no)
    pur.total_amount = total
    return pur

# Purchase 1 â€” 20 days ago (initial stock)
make_purchase(suppliers[0], [
    (products[0], 100, 30), (products[1], 80, 45),
    (products[2], 120, 18), (products[3], 200, 12),
    (products[4], 150, 10), (products[5], 100, 22),
], days_ago=20)

# Purchase 2 â€” 15 days ago
make_purchase(suppliers[1], [
    (products[8],  50, 65), (products[9], 30, 110),
    (products[10], 60, 50), (products[11], 40, 90),
    (products[12], 40, 280),(products[13], 60, 85),
], days_ago=15)

# Purchase 3 â€” 10 days ago
make_purchase(suppliers[2], [
    (products[15], 30, 580),(products[16], 50, 145),
    (products[17], 40, 165),(products[18], 80, 28),
    (products[19], 80, 35), (products[20], 80, 30),
    (products[21], 60, 55),
], days_ago=10)

# Purchase 4 â€” 5 days ago
make_purchase(suppliers[3], [
    (products[22], 100, 22),(products[23], 60, 85),
    (products[24], 80, 60), (products[25], 70, 60),
    (products[26], 80, 45), (products[27], 50, 75),
], days_ago=5)

# Purchase 5 â€” 2 days ago (top-up)
make_purchase(suppliers[4], [
    (products[6],  50, 35), (products[7],  80, 18),
    (products[14], 30, 180),(products[1],  50, 45),
    (products[0],  60, 30),
], days_ago=2)

db.flush()
print(f"  âœ“ 5 purchases done")

# â”€â”€ 7. SALES â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("Seeding salesâ€¦")

def make_sale(customer, items_data, paid_ratio=1.0, days_ago=0):
    dt = datetime.now() - timedelta(days=days_ago)
    sale = Sale(customer_id=customer.id, paid_amount=0, total_amount=0, due_amount=0,
                invoice_no="", created_at=dt)
    db.add(sale)
    db.flush()
    date_part = dt.strftime("%Y%m%d")
    sale.invoice_no = f"INV-{date_part}-{str(sale.id).zfill(5)}"
    total = 0
    for product, qty, rate in items_data:
        if product.current_stock < qty:
            qty = max(1, int(product.current_stock * 0.5))
        amt = qty * rate
        total += amt
        db.add(SaleItem(sale_id=sale.id, product_id=product.id, quantity=qty, rate=rate, amount=amt))
        log_stock(db=db, product=product, transaction_type="SALE",
                  quantity=qty, reference_id=sale.id, reference_no=sale.invoice_no)
    paid = round(total * paid_ratio)
    due = round(total - paid, 2)
    sale.total_amount = round(total, 2)
    sale.paid_amount = paid
    sale.due_amount = due
    customer.current_due = round(customer.current_due + due, 2)
    if paid > 0:
        log_payment(db=db, transaction_type="SALE_PAYMENT", amount=paid,
                    reference_no=sale.invoice_no, sale_id=sale.id,
                    customer_id=customer.id,
                    note=f"Payment on {sale.invoice_no}", created_by="systemadmin@gmail.com")
    return sale

# 18 days ago
s1 = make_sale(customers[0], [(products[0], 24, 40), (products[4], 30, 15), (products[8], 10, 85)], paid_ratio=1.0, days_ago=18)
s2 = make_sale(customers[1], [(products[12], 5, 350),(products[15], 2, 700),(products[22], 20, 30)], paid_ratio=0.7, days_ago=17)

# 12 days ago
s3 = make_sale(customers[2], [(products[1], 12, 60),(products[9], 5, 145),(products[23], 10, 115)], paid_ratio=1.0, days_ago=12)
s4 = make_sale(customers[3], [(products[3], 48, 18),(products[5], 20, 30),(products[25], 15, 80)], paid_ratio=0.5, days_ago=11)

# 7 days ago
s5 = make_sale(customers[4], [(products[2], 30, 25),(products[10], 8, 70),(products[18], 20, 40)], paid_ratio=1.0, days_ago=7)
s6 = make_sale(customers[5], [(products[16], 10, 185),(products[21], 10, 75),(products[24], 15, 80)], paid_ratio=0.8, days_ago=6)

# 3 days ago
s7 = make_sale(customers[6], [(products[6], 10, 50),(products[13], 5, 110),(products[26], 10, 60)], paid_ratio=1.0, days_ago=3)
s8 = make_sale(customers[7], [(products[7], 20, 25),(products[11], 5, 120),(products[27], 8, 100)], paid_ratio=0.6, days_ago=2)

# Today
s9  = make_sale(customers[0], [(products[0], 12, 40),(products[1], 6, 60),(products[4], 10, 15)], paid_ratio=1.0, days_ago=0)
s10 = make_sale(customers[2], [(products[8], 4, 85),(products[9], 2, 145),(products[12], 2, 350)], paid_ratio=0.75, days_ago=0)

db.flush()
print(f"  âœ“ 10 sales done")

# â”€â”€ 8. CUSTOMER PAYMENTS (due collections) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("Seeding due paymentsâ€¦")

def pay_due(sale, amount, days_ago=0):
    if sale.due_amount <= 0:
        return
    amount = min(amount, sale.due_amount)
    dt = datetime.now() - timedelta(days=days_ago)
    count = db.query(CustomerPayment).count()
    ref = f"PAY-{count+1:05d}"
    pmt = CustomerPayment(sale_id=sale.id, customer_id=sale.customer_id,
                          amount=amount, discount_amount=0, note="Due payment",
                          reference_no=ref, created_at=dt)
    db.add(pmt)
    sale.paid_amount = round(sale.paid_amount + amount, 2)
    sale.due_amount  = round(max(0, sale.due_amount - amount), 2)
    if sale.customer_id:
        cust = db.query(Customer).filter(Customer.id == sale.customer_id).first()
        if cust:
            cust.current_due = round(max(0, cust.current_due - amount), 2)
    log_payment(db=db, transaction_type="DUE_PAYMENT", amount=amount,
                reference_no=ref, sale_id=sale.id, customer_id=sale.customer_id,
                note=f"Due collected for {sale.invoice_no}", created_by="systemadmin@gmail.com")

pay_due(s2, 1000, days_ago=10)
pay_due(s4, 500,  days_ago=8)
pay_due(s6, 800,  days_ago=4)
pay_due(s8, 600,  days_ago=1)

db.commit()
print(f"  âœ“ 4 due payments done")

# â”€â”€ SUMMARY â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
from app.models.stock_transaction import StockTransaction
print("\nâœ… Seed complete!")
print(f"   Categories : {db.query(Category).count()}")
print(f"   Products   : {db.query(Product).count()}")
print(f"   Suppliers  : {db.query(Supplier).count()}")
print(f"   Customers  : {db.query(Customer).count()}")
print(f"   Purchases  : {db.query(Purchase).count()}")
print(f"   Sales      : {db.query(Sale).count()}")
print(f"   Payments   : {db.query(CustomerPayment).count()}")
print(f"   Stock logs : {db.query(StockTransaction).count()}")
db.close()
