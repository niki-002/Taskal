from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.core.errors import ConflictError
from app.models.auth import User
from app.schemas.user import UserUpdate
from app.services.user import UserService


# ---- UserService（DB不要） ----

class FakeUserRepository:
    def __init__(self, users: list[User], fail_on_save: bool = False):
        self.users = users
        self.fail_on_save = fail_on_save
        self.saved: list[User] = []

    async def get_by_username(self, username: str) -> User | None:
        return next((u for u in self.users if u.username == username), None)

    async def save(self, user: User) -> User:
        if self.fail_on_save:
            raise IntegrityError("UPDATE users", {}, Exception("duplicate"))
        self.saved.append(user)
        return user


def _make_user(user_id: int, username: str) -> User:
    return User(
        id=user_id,
        username=username,
        email=f"{username}@example.com",
        auth_subject=f"auth0|{username}",
        created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )


@pytest.mark.anyio
async def test_service_update_me_saves_new_username():
    me = _make_user(1, "before")
    repository = FakeUserRepository([me])

    response = await UserService(repository).update_me(UserUpdate(username="after"), me)

    assert response.username == "after"
    assert repository.saved == [me]


@pytest.mark.anyio
async def test_service_update_me_with_same_username_does_not_save():
    me = _make_user(1, "same")
    repository = FakeUserRepository([me])

    response = await UserService(repository).update_me(UserUpdate(username="same"), me)

    assert response.username == "same"
    assert repository.saved == []


@pytest.mark.anyio
async def test_service_update_me_with_taken_username_raises_conflict():
    me = _make_user(1, "me")
    repository = FakeUserRepository([me, _make_user(2, "taken")])

    with pytest.raises(ConflictError):
        await UserService(repository).update_me(UserUpdate(username="taken"), me)
    assert repository.saved == []


@pytest.mark.anyio
async def test_service_update_me_converts_integrity_error_to_conflict():
    me = _make_user(1, "me")
    repository = FakeUserRepository([me], fail_on_save=True)

    with pytest.raises(ConflictError):
        await UserService(repository).update_me(UserUpdate(username="race"), me)


# ---- Users API（DB使用） ----


def test_get_me_returns_current_user(client: TestClient, auth_headers):
    headers = auth_headers(sub="auth0|me", email="me@example.com")

    response = client.get("/api/v1/users/me", headers=headers)

    assert response.status_code == 200
    me = response.json()
    assert set(me) == {"id", "email", "username", "created_at"}
    assert me["id"] > 0
    assert me["email"] == "me@example.com"
    assert me["username"]
    assert datetime.fromisoformat(me["created_at"]).tzinfo is not None


def test_get_me_without_email_claim(client: TestClient, auth_headers):
    response = client.get("/api/v1/users/me", headers=auth_headers())

    assert response.status_code == 200
    assert response.json()["email"] is None


def test_get_me_reflects_email_synced_from_auth0(client: TestClient, auth_headers):
    response = client.get(
        "/api/v1/users/me",
        headers=auth_headers(sub="auth0|sync", email="old@example.com"),
    )
    user_id = response.json()["id"]

    response = client.get(
        "/api/v1/users/me",
        headers=auth_headers(sub="auth0|sync", email="new@example.com"),
    )

    assert response.status_code == 200
    assert response.json()["id"] == user_id
    assert response.json()["email"] == "new@example.com"


def test_get_me_is_owner_of_tasks(client: TestClient, authenticated_user):
    response = client.post(
        "/api/v1/tasks",
        json={"title": "task", "description": "", "limit": "2026-05-01"},
        headers=authenticated_user["headers"],
    )
    owner_id = response.json()["owner_id"]

    response = client.get("/api/v1/users/me", headers=authenticated_user["headers"])

    assert response.json()["id"] == owner_id


def test_update_me_changes_username(client: TestClient, authenticated_user):
    before = client.get("/api/v1/users/me", headers=authenticated_user["headers"]).json()

    response = client.patch(
        "/api/v1/users/me",
        json={"username": "new-taskal-user"},
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["username"] == "new-taskal-user"
    assert updated["id"] == before["id"]
    assert updated["email"] == before["email"]
    assert updated["created_at"] == before["created_at"]

    response = client.get("/api/v1/users/me", headers=authenticated_user["headers"])
    assert response.json()["username"] == "new-taskal-user"


def test_update_me_strips_whitespace(client: TestClient, authenticated_user):
    response = client.patch(
        "/api/v1/users/me",
        json={"username": "  spaced-user  "},
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 200
    assert response.json()["username"] == "spaced-user"


def test_update_me_with_same_username(client: TestClient, authenticated_user):
    username = client.get("/api/v1/users/me", headers=authenticated_user["headers"]).json()["username"]

    response = client.patch(
        "/api/v1/users/me",
        json={"username": username},
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 200
    assert response.json()["username"] == username


def test_update_me_with_taken_username_returns_409(client: TestClient, auth_headers):
    first_headers = auth_headers(sub="auth0|first")
    second_headers = auth_headers(sub="auth0|second")
    response = client.patch(
        "/api/v1/users/me",
        json={"username": "taken-name"},
        headers=first_headers,
    )
    assert response.status_code == 200
    before = client.get("/api/v1/users/me", headers=second_headers).json()

    response = client.patch(
        "/api/v1/users/me",
        json={"username": "taken-name"},
        headers=second_headers,
    )

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "CONFLICT"
    assert error["details"] == [{"field": "username", "reason": "already_exists"}]

    after = client.get("/api/v1/users/me", headers=second_headers).json()
    assert after["username"] == before["username"]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"username": None},
        {"username": ""},
        {"username": "   "},
        {"username": "a" * 51},
        {"username": 123},
    ],
)
def test_update_me_invalid_username_returns_422(client: TestClient, authenticated_user, payload):
    response = client.patch(
        "/api/v1/users/me",
        json=payload,
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"][0]["field"] == "username"


def test_update_me_accepts_max_length_username(client: TestClient, authenticated_user):
    response = client.patch(
        "/api/v1/users/me",
        json={"username": "a" * 50},
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 200


def test_update_me_ignores_email(client: TestClient, auth_headers):
    headers = auth_headers(sub="auth0|email", email="auth0@example.com")

    response = client.patch(
        "/api/v1/users/me",
        json={"username": "email-user", "email": "changed@example.com"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["email"] == "auth0@example.com"


@pytest.mark.parametrize("method", ["get", "patch"])
def test_users_me_without_token_returns_401(client: TestClient, method):
    response = client.request(method, "/api/v1/users/me", json={"username": "x"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
