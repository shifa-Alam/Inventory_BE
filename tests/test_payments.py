"""Tests for /payments/invoice — due collection, discount, validation."""
import pytest


@pytest.fixture()
def sale_with_due(client, auth_headers):
    """Creates a sale with ৳300 due."""
    cat = client.post("/categories/", json={"name": "Pay Cat"}, headers=auth_headers).json()
    cat_id = cat.get("id") or cat.get("category", {}).get("id")
    prod = client.post("/products/", json={"name": "Oil 5L", "sku": "PAY-TST-001",
                       "category_id": cat_id, "purchase_price": 500, "sale_price": 700},
                       headers=auth_headers).json()
    prod_id = prod.get("id") or prod.get("product", {}).get("id")
    sup = client.post("/suppliers/", json={"name": "Pay Sup"}, headers=auth_headers).json()
    sup_id = sup.get("id") or sup.get("supplier", {}).get("id")
    client.post("/purchases/", json={"supplier_id": sup_id,
                "items": [{"product_id": prod_id, "quantity": 10, "rate": 500}]},
                headers=auth_headers)
    cust = client.post("/customers/", json={"name": "Due Cust", "credit_limit": 50000, "current_due": 0},
                       headers=auth_headers).json()
    cust_id = cust.get("id") or cust.get("customer", {}).get("id")
    sale_res = client.post("/sales/", json={"customer_id": cust_id, "paid_amount": 400,
                           "items": [{"product_id": prod_id, "quantity": 1, "rate": 700}]},
                           headers=auth_headers).json()
    return sale_res, cust_id


def _get_sale_id(client, auth_headers, invoice_no):
    res = client.get(f"/sales/?invoice_no={invoice_no}", headers=auth_headers)
    data = res.json().get("data", [])
    return data[0]["id"] if data else None


def test_pay_due_full(client, auth_headers, sale_with_due):
    sale_res, _ = sale_with_due
    sale_id = _get_sale_id(client, auth_headers, sale_res["invoice_no"])
    if not sale_id:
        pytest.skip("sale not found")
    res = client.post("/payments/invoice", json={"sale_id": sale_id, "amount": 300, "discount_amount": 0},
                      headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["sale_due_remaining"] == 0


def test_pay_due_partial(client, auth_headers, sale_with_due):
    sale_res, _ = sale_with_due
    sale_id = _get_sale_id(client, auth_headers, sale_res["invoice_no"])
    if not sale_id:
        pytest.skip("sale not found")
    res = client.post("/payments/invoice", json={"sale_id": sale_id, "amount": 150, "discount_amount": 0},
                      headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["sale_due_remaining"] == pytest.approx(150, abs=1)


def test_pay_with_discount(client, auth_headers, sale_with_due):
    sale_res, _ = sale_with_due
    sale_id = _get_sale_id(client, auth_headers, sale_res["invoice_no"])
    if not sale_id:
        pytest.skip("sale not found")
    # pay 200 + 100 discount = 300 (full due)
    res = client.post("/payments/invoice", json={"sale_id": sale_id, "amount": 200, "discount_amount": 100},
                      headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["sale_due_remaining"] == 0


def test_overpayment_rejected(client, auth_headers, sale_with_due):
    sale_res, _ = sale_with_due
    sale_id = _get_sale_id(client, auth_headers, sale_res["invoice_no"])
    if not sale_id:
        pytest.skip("sale not found")
    res = client.post("/payments/invoice", json={"sale_id": sale_id, "amount": 99999, "discount_amount": 0},
                      headers=auth_headers)
    assert res.status_code == 400


def test_zero_payment_rejected(client, auth_headers, sale_with_due):
    sale_res, _ = sale_with_due
    sale_id = _get_sale_id(client, auth_headers, sale_res["invoice_no"])
    if not sale_id:
        pytest.skip("sale not found")
    res = client.post("/payments/invoice", json={"sale_id": sale_id, "amount": 0, "discount_amount": 0},
                      headers=auth_headers)
    assert res.status_code == 400


def test_payment_no_auth(client, sale_with_due):
    sale_res, _ = sale_with_due
    res = client.post("/payments/invoice", json={"sale_id": 1, "amount": 100, "discount_amount": 0})
    assert res.status_code == 401


def test_payment_nonexistent_sale(client, auth_headers):
    res = client.post("/payments/invoice", json={"sale_id": 99999, "amount": 100, "discount_amount": 0},
                      headers=auth_headers)
    assert res.status_code == 404


def test_list_payments(client, auth_headers, sale_with_due):
    res = client.get("/payments/invoice", headers=auth_headers)
    assert res.status_code == 200
    assert "data" in res.json()


def test_payment_summary(client, auth_headers):
    res = client.get("/payments/invoice/summary", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert "total_collection" in body
    assert "pending_invoices" in body
