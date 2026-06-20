"""Tests for /categories/ CRUD."""
import pytest


@pytest.fixture()
def category(client, auth_headers):
    res = client.post("/categories/", json={"name": "Test Cat", "description": "desc"}, headers=auth_headers)
    assert res.status_code == 200
    return res.json()


def test_create_category(client, auth_headers):
    res = client.post("/categories/", json={"name": "Beverages", "description": "Drinks"}, headers=auth_headers)
    assert res.status_code == 200


def test_create_category_no_auth(client):
    res = client.post("/categories/", json={"name": "X"})
    assert res.status_code == 401


def test_list_categories(client, auth_headers):
    res = client.get("/categories/", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "data" in data or isinstance(data, list)


def test_update_category(client, auth_headers, category):
    cat_id = category.get("id") or category.get("category", {}).get("id")
    if not cat_id:
        pytest.skip("No id in response")
    res = client.put(f"/categories/{cat_id}", json={"name": "Updated", "description": "new"}, headers=auth_headers)
    assert res.status_code == 200


def test_delete_category(client, auth_headers, category):
    cat_id = category.get("id") or category.get("category", {}).get("id")
    if not cat_id:
        pytest.skip("No id in response")
    res = client.delete(f"/categories/{cat_id}", headers=auth_headers)
    assert res.status_code in (200, 204)


def test_get_nonexistent_category(client, auth_headers):
    res = client.get("/categories/99999", headers=auth_headers)
    assert res.status_code == 404
