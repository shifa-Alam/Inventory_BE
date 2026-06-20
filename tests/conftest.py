"""
Shared pytest fixtures — in-memory SQLite DB, test client, auth token.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app

TEST_DB_URL = "sqlite:///./test.db"

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    session = TestingSession()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture(scope="session")
def auth_token(client):
    """Seed admin user and return Bearer token."""
    from app.models.user import User
    db = TestingSession()
    if not db.query(User).filter(User.username == "admin@test.com").first():
        db.add(User(username="admin@test.com", password=hash_password("Test@1234"), role="system_admin"))
        db.commit()
    db.close()

    res = client.post("/auth/login", data={"username": "admin@test.com", "password": "Test@1234"})
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.fixture()
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}
