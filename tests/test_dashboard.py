"""Tests for /dashboard/ endpoint."""


def test_dashboard_requires_auth(client):
    res = client.get("/dashboard/")
    assert res.status_code == 401


def test_dashboard_returns_data(client, auth_headers):
    res = client.get("/dashboard/", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert "total_products" in body
    assert "today_sales" in body
    assert "month_sales" in body
    assert "sales_chart" in body
    assert isinstance(body["sales_chart"], list)
    assert len(body["sales_chart"]) == 7


def test_dashboard_low_stock_items(client, auth_headers):
    res = client.get("/dashboard/", headers=auth_headers)
    body = res.json()
    assert "low_stock_items" in body
    assert isinstance(body["low_stock_items"], list)


def test_dashboard_recent_sales(client, auth_headers):
    res = client.get("/dashboard/", headers=auth_headers)
    body = res.json()
    assert "recent_sales" in body
    assert isinstance(body["recent_sales"], list)


def test_dashboard_top_products(client, auth_headers):
    res = client.get("/dashboard/", headers=auth_headers)
    body = res.json()
    assert "top_products" in body
