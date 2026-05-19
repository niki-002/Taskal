from itertools import count
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    text,
)
from sqlalchemy.orm import sessionmaker

from api.core.config import settings
from api.db import get_db
from api.main import app


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_URL = settings.test_database_url
if not TEST_DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL is not set.")


BASELINE_METADATA = MetaData()
Table(
    "users",
    BASELINE_METADATA,
    Column("id", Integer, primary_key=True),
    Column("username", String(50), nullable=False),
    Column("email", String, nullable=False),
    Column("hashed_password", String, nullable=False),
)
Table(
    "tasks",
    BASELINE_METADATA,
    Column("id", Integer, primary_key=True),
    Column("title", String(200), nullable=False),
    Column("done_flag", Boolean, nullable=False),
)


def _make_alembic_config() -> Config:
    alembic_config = Config(str(PROJECT_ROOT / "alembic.ini"))
    alembic_config.set_main_option(
        "script_location",
        str(PROJECT_ROOT / "api" / "alembic"),
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


@pytest.fixture()
def client():
    alembic_config = _make_alembic_config()
    engine = create_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
    )
    _drop_test_schema(engine)
    BASELINE_METADATA.create_all(bind=engine)
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
