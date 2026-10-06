from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import get_db
from app.main import app
from app.models.auth import User
from app.services.auth_service import verify_access_token


TASK_PAYLOAD = {
    "title": "test task",
    "description": "This is auth test.",
    "limit": "2026-05-01",
}


# ---- トークン検証（DB不要） ----

def test_verify_access_token_returns_claims(make_token):
    token = make_token(sub="auth0|abc", email="abc@example.com")

    payload = verify_access_token(token)

    assert payload["sub"] == "auth0|abc"


def test_verify_access_token_rejects_expired_token(make_token):
    expired = datetime.now(timezone.utc) - timedelta(minutes=1)
    token = make_token(exp=expired)

    with pytest.raises(HTTPException) as exc_info:
        verify_access_token(token)
    assert exc_info.value.status_code == 401


def test_verify_access_token_rejects_wrong_audience(make_token):
    token = make_token(aud="https://other-api.example.com")

    with pytest.raises(HTTPException) as exc_info:
        verify_access_token(token)
    assert exc_info.value.status_code == 401


def test_verify_access_token_rejects_wrong_issuer(make_token):
    token = make_token(iss="https://evil.example.com/")

    with pytest.raises(HTTPException) as exc_info:
        verify_access_token(token)
    assert exc_info.value.status_code == 401


def test_verify_access_token_rejects_invalid_signature(make_token):
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = make_token(private_key=other_key)

    with pytest.raises(HTTPException) as exc_info:
        verify_access_token(token)
    assert exc_info.value.status_code == 401


def test_verify_access_token_rejects_token_without_sub(make_token):
    token = make_token(sub=None)

    with pytest.raises(HTTPException) as exc_info:
        verify_access_token(token)
    assert exc_info.value.status_code == 401


# ---- APIでの認証（DB使用） ----

def test_request_without_token_returns_401(client: TestClient):
    response = client.get("/api/tasks")

    assert response.status_code == 401


def test_request_with_invalid_token_returns_401(client: TestClient):
    response = client.get(
        "/api/tasks",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_request_with_expired_token_returns_401(client: TestClient, make_token):
    expired = datetime.now(timezone.utc) - timedelta(minutes=1)
    token = make_token(exp=expired)

    response = client.get(
        "/api/tasks",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_first_access_creates_user(client: TestClient, auth_headers):
    headers = auth_headers(sub="auth0|first-access", email="first@example.com")

    response = client.get("/api/tasks", headers=headers)
    assert response.status_code == 200

    response = client.post("/api/tasks", json=TASK_PAYLOAD, headers=headers)
    assert response.status_code == 201

    db = next(app.dependency_overrides[get_db]())
    try:
        users = list(db.scalars(select(User).where(User.auth_subject == "auth0|first-access")))
    finally:
        db.close()
    assert len(users) == 1
    assert users[0].email == "first@example.com"
    assert users[0].username
    assert users[0].created_at is not None
    assert response.json()["owner_id"] == users[0].id


def test_same_subject_is_same_user(client: TestClient, auth_headers):
    first_headers = auth_headers(sub="auth0|same-user")
    second_headers = auth_headers(sub="auth0|same-user")

    response = client.post("/api/tasks", json=TASK_PAYLOAD, headers=first_headers)
    assert response.status_code == 201
    owner_id = response.json()["owner_id"]

    response = client.get("/api/tasks", headers=second_headers)
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 1
    assert tasks[0]["owner_id"] == owner_id


def test_password_auth_endpoints_are_removed(client: TestClient):
    response = client.post(
        "/api/auth/token",
        data={"username": "user@example.com", "password": "password123"},
    )

    assert response.status_code == 404
