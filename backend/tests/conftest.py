from datetime import datetime, timedelta, timezone
from itertools import count
from pathlib import Path

import jwt
import pytest
from alembic import command
from alembic.config import Config
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db import get_db
from app.main import app
from app.services import auth_service


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_URL = settings.test_database_url
if not TEST_DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL is not set.")


# Auth0の代わりにテスト用の鍵でトークンを署名する
TEST_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
TEST_PUBLIC_KEY = TEST_PRIVATE_KEY.public_key()


def _make_alembic_config() -> Config:
    alembic_config = Config(str(PROJECT_ROOT / "alembic.ini"))
    alembic_config.set_main_option(
        "script_location",
        str(PROJECT_ROOT / "alembic"),
    )
    alembic_config.set_main_option(
        "sqlalchemy.url",
        TEST_DATABASE_URL.replace("%", "%%"),
    )
    return alembic_config


def _run_migration(command_name: str, alembic_config: Config, revision: str) -> None:
    original_database_url = settings.database_url
    settings.database_url = TEST_DATABASE_URL
    try:
        getattr(command, command_name)(alembic_config, revision)
    finally:
        settings.database_url = original_database_url


def _drop_test_schema(engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS tasks CASCADE"))
        connection.execute(text("DROP TABLE IF EXISTS users CASCADE"))
        connection.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))


# JWKS(Auth0の公開鍵)の取得をモックし、テスト用の公開鍵を返す
@pytest.fixture(autouse=True)
def mock_signing_key(monkeypatch):
    monkeypatch.setattr(auth_service, "get_signing_key", lambda token: TEST_PUBLIC_KEY)


@pytest.fixture()
def make_token():
    def _make_token(
        sub: str = "auth0|test-user",
        email: str | None = None,
        private_key=TEST_PRIVATE_KEY,
        **overrides,
    ) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": sub,
            "iss": settings.auth0_issuer,
            "aud": settings.auth0_audience,
            "iat": now,
            "exp": now + timedelta(minutes=5),
        }
        if email is not None:
            payload[settings.auth0_email_claim] = email
        payload.update(overrides)
        payload = {key: value for key, value in payload.items() if value is not None}
        return jwt.encode(payload, private_key, algorithm="RS256")

    return _make_token


@pytest.fixture()
def client():
    alembic_config = _make_alembic_config()
    engine = create_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
    )
    _drop_test_schema(engine)
    _run_migration("upgrade", alembic_config, "head")

    testing_session = sessionmaker(
        autoflush=False,
        autocommit=False,
        bind=engine,
    )

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        _drop_test_schema(engine)
        engine.dispose()


@pytest.fixture()
def auth_headers(make_token):
    user_numbers = count(1)

    def _auth_headers(sub: str | None = None, email: str | None = None):
        sub = sub or f"auth0|user{next(user_numbers)}"
        token = make_token(sub=sub, email=email)
        return {"Authorization": f"Bearer {token}"}

    return _auth_headers


@pytest.fixture()
def authenticated_user(auth_headers):
    return {
        "sub": "auth0|authenticated-user",
        "headers": auth_headers(sub="auth0|authenticated-user"),
    }
