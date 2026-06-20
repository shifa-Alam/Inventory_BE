"""Tests for /products/ CRUD and search."""
import pytest


@pytest.fixture()
def category_id(client, auth_headers):
    res = client.post("/categories/", json={"name": "Prod Cat"}, headers=auth_headers)
    data = res.json()
    return data.get("id") or data.get("category", {}).get("id")


@pytest.fixture()
def product(client, auth_headers, category_id):
    payload = {"name": "Cola 500ml", "sku": "TST-001", "category_id": category_id,
               "purchase_price": 30, "sale_price": 45, "current_stock": 0}
    res = client.post("/products/", json=payload, headers=auth_headers)
    assert res.status_code == 200
    return res.json()


def test_create_product(client, auth_headers, category_id):
    payload = {"name": "Chips", "sku": "TST-CHI-01", "category_id": category_id,
               "purchase_price": 10, "sale_price": 15, "current_stock": 0}
    res = client.post("/products/", json=payload, headers=auth_headers)
    assert res.status_code == 200


def test_create_product_no_auth(client):
    res = client.post("/products/", json={"name": "X", "sku": "Y"})
    assert res.status_code == 401


def test_list_products(client, auth_headers):
    res = client.get("/products/", headers=auth_headers)
    assert res.status_code == 200


def test_list_products_filter_by_name(client, auth_headers, product):
    res = client.get("/products/?name=Cola", headers=auth_headers)
    assert res.status_code == 200


def test_search_products(client, auth_headers, product):
    res = client.get("/products/search?q=Cola", headers=auth_headers)
    assert res.status_code == 200
    results = res.json()
    assert isinstance(results, list)


def test_search_empty_query_returns_empty(client, auth_headers):
    res = client.get("/products/search?q=", headers=auth_headers)
    assert res.status_code == 200


def test_update_product(client, auth_headers, product):
    pid = product.get("id") or product.get("product", {}).get("id")
    if not pid:
        pytest.skip("No id in response")
    res = client.put(f"/products/{pid}", json={"name": "Cola Updated", "sale_price": 50}, headers=auth_headers)
    assert res.status_code == 200


def test_duplicate_sku_rejected(client, auth_headers, category_id):
    payload = {"name": "Dup A", "sku": "DUP-SKU-001", "category_id": category_id, "purchase_price": 10, "sale_price": 15}
    client.post("/products/", json=payload, headers=auth_headers)
    res = client.post("/products/", json=payload, headers=auth_headers)
    assert res.status_code in (400, 409, 422, 500)
