"""Tests for /auth endpoints."""
import pytest


def test_login_success(client, auth_token):
    assert auth_token is not None and len(auth_token) > 10


def test_login_wrong_password(client):
    res = client.post("/auth/login", data={"username": "admin@test.com", "password": "wrong"})
    assert res.status_code == 401


def test_login_unknown_user(client):
    res = client.post("/auth/login", data={"username": "nobody@x.com", "password": "pass"})
    assert res.status_code == 401


def test_login_empty_credentials(client):
    res = client.post("/auth/login", data={"username": "", "password": ""})
    assert res.status_code in (401, 422)


def test_get_roles_requires_auth(client):
    res = client.get("/auth/roles")
    assert res.status_code == 401


def test_get_roles_with_auth(client, auth_headers):
    res = client.get("/auth/roles", headers=auth_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_no_token_returns_401_not_403(client):
    res = client.get("/categories/")
    assert res.status_code == 401
