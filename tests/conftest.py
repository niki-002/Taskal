from itertools import count

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.db import get_db
from api.main import app
from api.models.Base import Base
from api.models import auth, task  # noqa: F401
from api.core.config import settings


TEST_DATABASE_URL = settings.test_database_url
if not TEST_DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL is not set.")


@pytest.fixture()
def client():
    engine = create_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
    )
    testing_session = sessionmaker(
        autoflush=False,
        autocommit=False,
        bind=engine,
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    startup_handlers = list(app.router.on_startup)
    app.router.on_startup.clear()
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        app.router.on_startup[:] = startup_handlers
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def create_user(client: TestClient):
    user_numbers = count(1)

    def _create_user(email: str | None = None, password: str = "password123"):
        email = email or f"user{next(user_numbers)}@example.com"
        response = client.post(
            "/api/auth",
            data={
                "username": email,
                "password": password,
            },
        )
        assert response.status_code == 200
        user = response.json()
        return {
            "id": user["id"],
            "email": email,
            "password": password,
            "username": user["username"],
        }

    return _create_user


@pytest.fixture()
def login_user(client: TestClient):
    def _login_user(email: str, password: str):
        response = client.post(
            "/api/auth/token",
            data={
                "username": email,
                "password": password,
            },
        )
        assert response.status_code == 200
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _login_user


@pytest.fixture()
def authenticated_user(create_user, login_user):
    user = create_user()
    user["headers"] = login_user(user["email"], user["password"])
    return user
