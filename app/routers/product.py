from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin, get_tenant_id
from app.core.pagination import make_page
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate

router = APIRouter(
    prefix="/products",
    tags=["Products"],
    dependencies=[Depends(get_current_user)]
)


def _serialize(p: Product) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "sku": p.sku,
        "category_id": p.category_id,
        "purchase_price": p.purchase_price,
        "sale_price": p.sale_price,
        "mrp": p.mrp or 0,
        "current_stock": p.current_stock,
        "stock_value": (p.current_stock or 0) * (p.purchase_price or 0),
        "is_active": p.is_active if p.is_active is not None else True,
        "status": "LOW" if (p.current_stock or 0) <= 10 else "OK",
    }


@router.post("/")
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    existing = db.query(Product).filter(Product.sku == product.sku, Product.tenant_id == tenant_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="SKU already exists")

    db_product = Product(
        name=product.name,
        sku=product.sku,
        category_id=product.category_id,
        purchase_price=product.purchase_price,
        sale_price=product.sale_price,
        mrp=product.mrp,
        current_stock=product.current_stock,
        is_active=True,
        tenant_id=tenant_id,
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return _serialize(db_product)


@router.get("/search")
def search_products(q: str, db: Session = Depends(get_db), tenant_id: int = Depends(get_tenant_id)):
    """Active-only search used by sales and purchase forms."""
    sku_match = db.query(Product).filter(
        Product.sku == q, Product.is_active == True, Product.tenant_id == tenant_id
    ).first()
    if sku_match:
        return [_serialize(sku_match)]
    return [
        _serialize(p) for p in
        db.query(Product)
          .filter(Product.name.ilike(f"%{q}%"), Product.is_active == True, Product.tenant_id == tenant_id)
          .limit(10).all()
    ]


@router.get("/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db), tenant_id: int = Depends(get_tenant_id)):
    product = db.query(Product).filter(Product.id == product_id, Product.tenant_id == tenant_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _serialize(product)


@router.put("/{product_id}")
def update_product(
    product_id: int,
    product: ProductUpdate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    db_product = db.query(Product).filter(Product.id == product_id, Product.tenant_id == tenant_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    # SKU uniqueness check scoped to tenant
    if product.sku != db_product.sku:
        conflict = db.query(Product).filter(
            Product.sku == product.sku, Product.tenant_id == tenant_id, Product.id != product_id
        ).first()
        if conflict:
            raise HTTPException(status_code=400, detail="SKU already exists")

    db_product.name = product.name
    db_product.sku = product.sku
    db_product.category_id = product.category_id
    db_product.purchase_price = product.purchase_price
    db_product.sale_price = product.sale_price
    db_product.mrp = product.mrp

    db.commit()
    db.refresh(db_product)
    return _serialize(db_product)


@router.patch("/{product_id}/toggle-active")
def toggle_active(
    product_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    db_product = db.query(Product).filter(Product.id == product_id, Product.tenant_id == tenant_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    db_product.is_active = not (db_product.is_active if db_product.is_active is not None else True)
    db.commit()
    db.refresh(db_product)
    return _serialize(db_product)


@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
    tenant_id: int = Depends(get_tenant_id),
):
    db_product = db.query(Product).filter(Product.id == product_id, Product.tenant_id == tenant_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(db_product)
    db.commit()
    return {"message": "Product deleted"}


@router.get("/")
def get_products(
    name: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
):
    query = db.query(Product).filter(Product.tenant_id == tenant_id)
    if name:
        query = query.filter(Product.name.ilike(f"%{name}%"))
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if status == "LOW":
        query = query.filter(Product.current_stock <= 10)
    elif status == "OK":
        query = query.filter(Product.current_stock > 10)
    if is_active is not None:
        query = query.filter(Product.is_active == is_active)

    total = query.count()
    products = query.offset((page - 1) * page_size).limit(page_size).all()
    return make_page([_serialize(p) for p in products], total, page, page_size)
