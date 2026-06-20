"""Tests for /customers/ CRUD and filtering."""
import pytest


@pytest.fixture()
def customer(client, auth_headers):
    res = client.post("/customers/", json={"name": "Test Shop", "phone": "01799000001",
                      "address": "Dhaka", "credit_limit": 5000, "current_due": 0},
                      headers=auth_headers)
    assert res.status_code == 200
    return res.json()


def test_create_customer(client, auth_headers):
    res = client.post("/customers/", json={"name": "New Shop", "phone": "01799000099"},
                      headers=auth_headers)
    assert res.status_code == 200


def test_create_customer_no_auth(client):
    res = client.post("/customers/", json={"name": "X"})
    assert res.status_code == 401


def test_list_customers(client, auth_headers, customer):
    res = client.get("/customers/", headers=auth_headers)
    assert res.status_code == 200
    assert "data" in res.json()


def test_filter_customers_by_name(client, auth_headers, customer):
    res = client.get("/customers/?name=Test", headers=auth_headers)
    assert res.status_code == 200


def test_filter_customers_with_due(client, auth_headers):
    res = client.get("/customers/?has_due=true", headers=auth_headers)
    assert res.status_code == 200
    for c in res.json().get("data", []):
        assert c["current_due"] > 0


def test_update_customer(client, auth_headers, customer):
    cid = customer.get("id") or customer.get("customer", {}).get("id")
    if not cid:
        pytest.skip()
    res = client.put(f"/customers/{cid}", json={"name": "Updated Shop", "phone": "01799000001",
                     "address": "Chittagong", "credit_limit": 8000, "current_due": 0},
                     headers=auth_headers)
    assert res.status_code == 200


def test_delete_customer(client, auth_headers):
    c = client.post("/customers/", json={"name": "Del Me"}, headers=auth_headers).json()
    cid = c.get("id") or c.get("customer", {}).get("id")
    if not cid:
        pytest.skip()
    res = client.delete(f"/customers/{cid}", headers=auth_headers)
    assert res.status_code in (200, 204)


def test_get_nonexistent_customer(client, auth_headers):
    res = client.get("/customers/99999", headers=auth_headers)
    assert res.status_code == 404
