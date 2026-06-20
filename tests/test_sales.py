"""Tests for /sales/ — create, list, filter, stock deduction, due calculation."""
import pytest
from datetime import date


@pytest.fixture()
def setup(client, auth_headers):
    """Returns (customer_id, product_id) with stocked product."""
    cat = client.post("/categories/", json={"name": "Sale Cat"}, headers=auth_headers).json()
    cat_id = cat.get("id") or cat.get("category", {}).get("id")
    prod = client.post("/products/", json={"name": "Juice 1L", "sku": "SAL-TST-001",
                       "category_id": cat_id, "purchase_price": 40, "sale_price": 60, "current_stock": 0},
                       headers=auth_headers).json()
    prod_id = prod.get("id") or prod.get("product", {}).get("id")
    sup = client.post("/suppliers/", json={"name": "Sal Sup"}, headers=auth_headers).json()
    sup_id = sup.get("id") or sup.get("supplier", {}).get("id")
    # Stock in 50 units
    client.post("/purchases/", json={"supplier_id": sup_id,
                "items": [{"product_id": prod_id, "quantity": 50, "rate": 40}]},
                headers=auth_headers)
    cust = client.post("/customers/", json={"name": "Test Customer", "phone": "01799999001",
                        "address": "Dhaka", "credit_limit": 10000, "current_due": 0},
                       headers=auth_headers).json()
    cust_id = cust.get("id") or cust.get("customer", {}).get("id")
    return cust_id, prod_id


@pytest.fixture()
def sale(client, auth_headers, setup):
    cust_id, prod_id = setup
    payload = {"customer_id": cust_id, "paid_amount": 120,
               "items": [{"product_id": prod_id, "quantity": 2, "rate": 60}]}
    res = client.post("/sales/", json=payload, headers=auth_headers)
    assert res.status_code == 200
    return res.json()


def test_create_sale_full_payment(sale):
    assert "invoice_no" in sale
    assert sale["due"] == 0


def test_create_sale_partial_payment(client, auth_headers, setup):
    cust_id, prod_id = setup
    payload = {"customer_id": cust_id, "paid_amount": 60,
               "items": [{"product_id": prod_id, "quantity": 2, "rate": 60}]}
    res = client.post("/sales/", json=payload, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["due"] == 60


def test_sale_no_auth(client, setup):
    cust_id, prod_id = setup
    res = client.post("/sales/", json={"customer_id": cust_id, "paid_amount": 0, "items": []})
    assert res.status_code == 401


def test_sale_out_of_stock(client, auth_headers, setup):
    cust_id, prod_id = setup
    res = client.post("/sales/", json={"customer_id": cust_id, "paid_amount": 0,
                      "items": [{"product_id": prod_id, "quantity": 99999, "rate": 60}]},
                      headers=auth_headers)
    assert res.status_code == 400


def test_sale_paid_exceeds_total(client, auth_headers, setup):
    cust_id, prod_id = setup
    res = client.post("/sales/", json={"customer_id": cust_id, "paid_amount": 99999,
                      "items": [{"product_id": prod_id, "quantity": 1, "rate": 60}]},
                      headers=auth_headers)
    assert res.status_code == 400


def test_sale_reduces_stock(client, auth_headers, setup):
    cust_id, prod_id = setup
    before = client.get(f"/products/{prod_id}", headers=auth_headers).json()
    stock_before = before.get("current_stock", 0)
    client.post("/sales/", json={"customer_id": cust_id, "paid_amount": 60,
                "items": [{"product_id": prod_id, "quantity": 1, "rate": 60}]},
                headers=auth_headers)
    after = client.get(f"/products/{prod_id}", headers=auth_headers).json()
    assert after.get("current_stock", 0) == stock_before - 1


def test_sale_updates_customer_due(client, auth_headers, setup):
    cust_id, prod_id = setup
    before = client.get(f"/customers/{cust_id}", headers=auth_headers).json()
    due_before = before.get("current_due", 0)
    client.post("/sales/", json={"customer_id": cust_id, "paid_amount": 0,
                "items": [{"product_id": prod_id, "quantity": 2, "rate": 60}]},
                headers=auth_headers)
    after = client.get(f"/customers/{cust_id}", headers=auth_headers).json()
    assert after.get("current_due", 0) == due_before + 120


def test_list_sales(client, auth_headers, sale):
    res = client.get("/sales/", headers=auth_headers)
    assert res.status_code == 200
    assert "data" in res.json()


def test_list_sales_filter_by_customer(client, auth_headers, setup, sale):
    cust_id, _ = setup
    res = client.get(f"/sales/?customer_id={cust_id}", headers=auth_headers)
    assert res.status_code == 200


def test_list_sales_filter_by_date(client, auth_headers, sale):
    today = date.today().isoformat()
    res = client.get(f"/sales/?date_from={today}&date_to={today}", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()["data"]) >= 1


def test_list_sales_filter_has_due(client, auth_headers, setup):
    cust_id, prod_id = setup
    client.post("/sales/", json={"customer_id": cust_id, "paid_amount": 0,
                "items": [{"product_id": prod_id, "quantity": 1, "rate": 60}]},
                headers=auth_headers)
    res = client.get("/sales/?has_due=true", headers=auth_headers)
    assert res.status_code == 200
    for s in res.json()["data"]:
        assert s["due_amount"] > 0


def test_invoice_no_format(sale):
    assert sale["invoice_no"].startswith("INV-")
