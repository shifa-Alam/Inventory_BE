"""Tests for /purchases/ — create, list, filter, detail."""
import pytest
from datetime import date


@pytest.fixture()
def setup(client, auth_headers):
    """Returns (supplier_id, product_id) for purchase tests."""
    sup = client.post("/suppliers/", json={"name": "Test Sup", "phone": "01700000001", "address": "Dhaka"}, headers=auth_headers).json()
    cat = client.post("/categories/", json={"name": "Pur Cat"}, headers=auth_headers).json()
    cat_id = cat.get("id") or cat.get("category", {}).get("id")
    prod = client.post("/products/", json={"name": "Rice 5kg", "sku": "PUR-TST-001",
                       "category_id": cat_id, "purchase_price": 280, "sale_price": 350, "current_stock": 0},
                       headers=auth_headers).json()
    sup_id = sup.get("id") or sup.get("supplier", {}).get("id")
    prod_id = prod.get("id") or prod.get("product", {}).get("id")
    return sup_id, prod_id


@pytest.fixture()
def purchase(client, auth_headers, setup):
    sup_id, prod_id = setup
    payload = {
        "supplier_id": sup_id,
        "items": [{"product_id": prod_id, "quantity": 10, "rate": 280}],
        "total_amount": 2800
    }
    res = client.post("/purchases/", json=payload, headers=auth_headers)
    assert res.status_code == 200
    return res.json()


def test_create_purchase(purchase):
    assert "invoice_no" in purchase or "message" in purchase


def test_purchase_no_auth(client, setup):
    sup_id, prod_id = setup
    res = client.post("/purchases/", json={"supplier_id": sup_id, "items": []})
    assert res.status_code == 401


def test_purchase_missing_supplier(client, auth_headers, setup):
    _, prod_id = setup
    res = client.post("/purchases/", json={"supplier_id": 99999,
                      "items": [{"product_id": prod_id, "quantity": 5, "rate": 280}]},
                      headers=auth_headers)
    assert res.status_code in (400, 404, 422)


def test_purchase_invalid_product(client, auth_headers, setup):
    sup_id, _ = setup
    res = client.post("/purchases/", json={"supplier_id": sup_id,
                      "items": [{"product_id": 99999, "quantity": 5, "rate": 280}]},
                      headers=auth_headers)
    assert res.status_code in (400, 404)


def test_list_purchases(client, auth_headers, purchase):
    res = client.get("/purchases/", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert "data" in body


def test_list_purchases_filter_by_date(client, auth_headers, purchase):
    today = date.today().isoformat()
    res = client.get(f"/purchases/?date_from={today}&date_to={today}", headers=auth_headers)
    assert res.status_code == 200


def test_purchase_increases_stock(client, auth_headers, setup):
    sup_id, prod_id = setup
    before = client.get(f"/products/{prod_id}", headers=auth_headers).json()
    stock_before = before.get("current_stock", 0)
    client.post("/purchases/", json={"supplier_id": sup_id,
                "items": [{"product_id": prod_id, "quantity": 5, "rate": 280}]},
                headers=auth_headers)
    after = client.get(f"/products/{prod_id}", headers=auth_headers).json()
    assert after.get("current_stock", 0) == stock_before + 5
