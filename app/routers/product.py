from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.core.pagination import make_page
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate

router = APIRouter(
    prefix="/products",
    tags=["Products"],
    dependencies=[Depends(get_current_user)]
)


# GET ALL PRODUCTS
# @router.get("/")
# def get_products(db: Session = Depends(get_db)):
#     return db.query(Product).all()


# CREATE PRODUCT
@router.post("/")
def create_product(product: ProductCreate, db: Session = Depends(get_db)):

    existing = db.query(Product).filter(Product.sku == product.sku).first()
    if existing:
        raise HTTPException(status_code=400, detail="SKU already exists")

    db_product = Product(
        name=product.name,
        sku=product.sku,
        category_id=product.category_id,
        purchase_price=product.purchase_price,
        sale_price=product.sale_price,
        mrp=product.mrp,
        current_stock=product.current_stock
    )

    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    return db_product


@router.get("/search")
def search_products(q: str, db: Session = Depends(get_db)):
    sku_match = db.query(Product).filter(Product.sku == q).first()
    if sku_match:
        return [sku_match]
    return db.query(Product).filter(
        Product.name.ilike(f"%{q}%")
    ).limit(10).all()

# GET BY ID


@router.get("/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


# UPDATE PRODUCT
@router.put("/{product_id}")
def update_product(product_id: int, product: ProductUpdate, db: Session = Depends(get_db)):
    db_product = db.query(Product).filter(Product.id == product_id).first()

    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    db_product.name = product.name
    db_product.sku = product.sku
    db_product.category_id = product.category_id
    db_product.purchase_price = product.purchase_price
    db_product.sale_price = product.sale_price
    db_product.mrp = product.mrp

    db.commit()
    db.refresh(db_product)

    return db_product


# DELETE PRODUCT
@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    db_product = db.query(Product).filter(Product.id == product_id).first()

    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(db_product)
    db.commit()

    return {"message": "Product deleted"}


@router.get("/")
def get_products(
    name: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None, description="OK or LOW"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    query = db.query(Product)

    if name:
        query = query.filter(Product.name.ilike(f"%{name}%"))
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if status == "LOW":
        query = query.filter(Product.current_stock <= 10)
    elif status == "OK":
        query = query.filter(Product.current_stock > 10)

    total = query.count()
    products = query.offset((page - 1) * page_size).limit(page_size).all()

    result = []
    for p in products:
        result.append({
            "id": p.id,
            "name": p.name,
            "sku": p.sku,
            "category_id": p.category_id,
            "purchase_price": p.purchase_price,
            "sale_price": p.sale_price,
            "mrp": p.mrp or 0,
            "current_stock": p.current_stock,
            "stock_value": (p.current_stock or 0) * (p.purchase_price or 0),
            "status": "LOW" if p.current_stock <= 10 else "OK"
        })

    return make_page(result, total, page, page_size)
