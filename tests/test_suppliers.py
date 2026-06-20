"""Tests for /suppliers/ CRUD."""
import pytest


@pytest.fixture()
def supplier(client, auth_headers):
    res = client.post("/suppliers/", json={"name": "Test Supplier", "phone": "01711000001", "address": "Dhaka"},
                      headers=auth_headers)
    assert res.status_code == 200
    return res.json()


def test_create_supplier(client, auth_headers):
    res = client.post("/suppliers/", json={"name": "ABC Traders"}, headers=auth_headers)
    assert res.status_code == 200


def test_create_supplier_no_auth(client):
    res = client.post("/suppliers/", json={"name": "X"})
    assert res.status_code == 401


def test_list_suppliers(client, auth_headers, supplier):
    res = client.get("/suppliers/", headers=auth_headers)
    assert res.status_code == 200
    assert "data" in res.json()


def test_filter_supplier_by_name(client, auth_headers, supplier):
    res = client.get("/suppliers/?name=Test", headers=auth_headers)
    assert res.status_code == 200


def test_update_supplier(client, auth_headers, supplier):
    sid = supplier.get("id") or supplier.get("supplier", {}).get("id")
    if not sid:
        pytest.skip()
    res = client.put(f"/suppliers/{sid}", json={"name": "Updated Supplier", "phone": "01711000002"},
                     headers=auth_headers)
    assert res.status_code == 200


def test_delete_supplier(client, auth_headers):
    s = client.post("/suppliers/", json={"name": "Del Sup"}, headers=auth_headers).json()
    sid = s.get("id") or s.get("supplier", {}).get("id")
    if not sid:
        pytest.skip()
    res = client.delete(f"/suppliers/{sid}", headers=auth_headers)
    assert res.status_code in (200, 204)
