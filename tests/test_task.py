from fastapi.testclient import TestClient


TASK_PAYLOAD = {
    "title": "test task",
    "description": "This is first test.",
    "limit": "2026-05-01",
}


def test_task_crud(client: TestClient, authenticated_user):
    response = client.post(
        "/api/tasks",
        json=TASK_PAYLOAD,
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 201
    task = response.json()
    task_id = task["id"]
    assert task["owner_id"] == authenticated_user["id"]
    assert task["title"] == TASK_PAYLOAD["title"]
    assert task["description"] == TASK_PAYLOAD["description"]
    assert task["limit"] == TASK_PAYLOAD["limit"]
    assert task["done_flag"] is False

    response = client.get(
        "/api/tasks",
        headers=authenticated_user["headers"],
    )
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 1
    assert tasks[0]["id"] == task_id

    response = client.get(
        f"/api/tasks/{task_id}",
        headers=authenticated_user["headers"],
    )
    assert response.status_code == 200
    assert response.json()["title"] == TASK_PAYLOAD["title"]

    update_payload = {
        "title": "updated task",
        "description": "This is second test.",
        "limit": "2026-06-01",
    }
    response = client.put(
        f"/api/tasks/{task_id}",
        json=update_payload,
        headers=authenticated_user["headers"],
    )
    assert response.status_code == 200
    updated_task = response.json()
    assert updated_task["title"] == update_payload["title"]
    assert updated_task["description"] == update_payload["description"]
    assert updated_task["limit"] == update_payload["limit"]

    response = client.delete(
        f"/api/tasks/{task_id}",
        headers=authenticated_user["headers"],
    )
    assert response.status_code == 204

    response = client.get(
        f"/api/tasks/{task_id}",
        headers=authenticated_user["headers"],
    )
    assert response.status_code == 404


def test_tasks_require_authentication(client: TestClient):
    response = client.get("/api/tasks")

    assert response.status_code == 401


def test_user_cannot_read_another_users_task(
    client: TestClient,
    create_user,
    login_user,
):
    first_user = create_user(email="first@example.com")
    first_headers = login_user(first_user["email"], first_user["password"])
    second_user = create_user(email="second@example.com")
    second_headers = login_user(second_user["email"], second_user["password"])

    response = client.post(
        "/api/tasks",
        json=TASK_PAYLOAD,
        headers=first_headers,
    )
    assert response.status_code == 201
    task_id = response.json()["id"]

    response = client.get(
        f"/api/tasks/{task_id}",
        headers=second_headers,
    )
    assert response.status_code == 404

    response = client.get(
        "/api/tasks",
        headers=second_headers,
    )
    assert response.status_code == 200
    assert response.json() == []
