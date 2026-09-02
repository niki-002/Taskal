from fastapi.testclient import TestClient


def test_register_user(client: TestClient):
    response = client.post(
        "/api/auth",
        data={
            "username": "new-user@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 200
    user = response.json()
    assert user["id"] > 0
    assert user["email"] == "new-user@example.com"
    assert user["username"]
    assert "hashed_password" not in user


def test_register_duplicate_email_returns_400(client: TestClient, create_user):
    create_user(email="duplicate@example.com")

    response = client.post(
        "/api/auth",
        data={
            "username": "duplicate@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "The email has already been used."


def test_login_returns_access_token(client: TestClient, create_user):
    user = create_user(email="login@example.com", password="password123")

    response = client.post(
        "/api/auth/token",
        data={
            "username": user["email"],
            "password": user["password"],
        },
    )

    assert response.status_code == 200
    token = response.json()
    assert token["access_token"]
    assert token["token_type"] == "bearer"


def test_login_with_wrong_password_returns_401(client: TestClient, create_user):
    user = create_user(email="wrong-password@example.com", password="password123")

    response = client.post(
        "/api/auth/token",
        data={
            "username": user["email"],
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


def test_read_users_me_returns_current_user(
    client: TestClient,
    authenticated_user,
):
    response = client.get(
        "/api/auth/users/me",
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 200
    user = response.json()
    assert user["id"] == authenticated_user["id"]
    assert user["email"] == authenticated_user["email"]
