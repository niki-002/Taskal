from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.errors import NotFoundError, ValidationError
from app.core.pagination import Cursor, PageParams
from app.models.auth import User
from app.models.schedule import Schedule
from app.models.task import Task
from app.schemas.schedule import ScheduleBaseCreate, ScheduleUpdate
from app.schemas.task import TaskCreate, TaskListParams, TaskUpdate
from app.services.task import TaskService

BASE_AT = datetime(2026, 9, 10, 4, 0, tzinfo=timezone.utc)


# ---- TaskService（DB不要） ----

class FakeTaskRepository:
    def __init__(self, tasks: list[Task] | None = None):
        self.tasks = tasks or []
        self.saved: list[Task] = []
        self.deleted: list[Task] = []
        self.list_calls: list[dict] = []

    async def get_by_id(self, schedule_id: int, owner_id: int) -> Task | None:
        return next(
            (
                t for t in self.tasks
                if t.schedule_id == schedule_id and t.schedule.user_id == owner_id
            ),
            None,
        )

    async def list_page(self, owner_id, limit, **filters):
        self.list_calls.append({"owner_id": owner_id, "limit": limit, **filters})
        return [t for t in self.tasks if t.schedule.user_id == owner_id][:limit + 1]

    async def add(self, task: Task) -> Task:
        task.schedule.id = task.schedule_id = len(self.tasks) + 1
        task.schedule.created_at = task.schedule.updated_at = BASE_AT
        self.tasks.append(task)
        return task

    async def save(self, task: Task) -> Task:
        self.saved.append(task)
        return task

    async def delete(self, task: Task) -> None:
        self.deleted.append(task)


class FakePlannedTransactionRepository:
    def __init__(self):
        self.deleted_schedule_ids: list[int] = []

    async def delete_unactualized_by_schedule(self, schedule_id: int) -> None:
        self.deleted_schedule_ids.append(schedule_id)


def _make_user(user_id: int = 1) -> User:
    return User(id=user_id, username=f"user{user_id}", auth_subject=f"auth0|user{user_id}")


def _make_task(schedule_id: int, user_id: int = 1, days: int = 0) -> Task:
    return Task(
        schedule_id=schedule_id,
        due_date=BASE_AT + timedelta(days=days),
        done_flag=False,
        schedule=Schedule(
            id=schedule_id,
            user_id=user_id,
            title=f"task{schedule_id}",
            description=None,
            start_at=BASE_AT,
            end_at=BASE_AT + timedelta(hours=1),
            kind="task",
            category=None,
            created_at=BASE_AT,
            updated_at=BASE_AT,
        ),
    )


def _make_service(tasks: list[Task] | None = None):
    repository = FakeTaskRepository(tasks)
    planned_transaction_repository = FakePlannedTransactionRepository()
    return (
        TaskService(repository, planned_transaction_repository),
        repository,
        planned_transaction_repository,
    )


@pytest.mark.anyio
async def test_service_create_task_sets_kind_done_flag_and_owner():
    service, repository, _ = _make_service()

    response = await service.create_task(
        TaskCreate(
            schedule=ScheduleBaseCreate(
                title="レポート提出",
                start_at=BASE_AT,
                end_at=BASE_AT + timedelta(hours=1),
                category="assignment",
            ),
            due_date=BASE_AT + timedelta(days=2),
        ),
        _make_user(7),
    )

    created = repository.tasks[0]
    assert created.schedule.user_id == 7
    assert created.schedule.kind == "task"
    assert created.done_flag is False
    assert response.schedule_id == response.schedule.id == 1
    assert response.schedule.kind == "task"
    assert response.schedule.category == "assignment"
    assert response.due_date == BASE_AT + timedelta(days=2)


@pytest.mark.anyio
async def test_service_get_other_users_task_raises_not_found():
    service, _, _ = _make_service([_make_task(1, user_id=2)])

    with pytest.raises(NotFoundError):
        await service.get_task(1, _make_user(1))


@pytest.mark.anyio
async def test_service_list_tasks_passes_filters_and_builds_next_cursor():
    tasks = [_make_task(i, days=i) for i in range(1, 4)]
    service, repository, _ = _make_service(tasks)

    page = await service.list_tasks(
        TaskListParams(done=False, due_from=BASE_AT, category="assignment"),
        PageParams(limit=2),
        _make_user(),
    )

    assert [item.schedule_id for item in page.items] == [1, 2]
    assert page.next_cursor == Cursor.encode(2)
    call = repository.list_calls[0]
    assert call["done"] is False
    assert call["due_from"] == BASE_AT
    assert call["due_to"] is None
    assert call["category"] == "assignment"
    assert call["after"] is None


@pytest.mark.anyio
async def test_service_list_tasks_continues_after_cursor_task():
    after = _make_task(5)
    service, repository, _ = _make_service([after])

    await service.list_tasks(TaskListParams(), PageParams(after_id=5), _make_user())

    assert repository.list_calls[0]["after"] is after


@pytest.mark.anyio
async def test_service_list_tasks_with_unknown_cursor_raises_validation_error():
    service, _, _ = _make_service([_make_task(5, user_id=2)])

    with pytest.raises(ValidationError):
        await service.list_tasks(TaskListParams(), PageParams(after_id=5), _make_user(1))


@pytest.mark.anyio
async def test_service_update_task_changes_task_and_schedule_fields():
    target = _make_task(1)
    target.schedule.description = "keep"
    service, repository, _ = _make_service([target])

    response = await service.update_task(
        1,
        TaskUpdate(
            done_flag=True,
            schedule=ScheduleUpdate(title="レポート提出済み", category=None),
        ),
        _make_user(),
    )

    assert response.done_flag is True
    assert response.due_date == BASE_AT
    assert response.schedule.title == "レポート提出済み"
    assert response.schedule.description == "keep"
    assert response.schedule.category is None
    assert repository.saved == [target]


@pytest.mark.anyio
async def test_service_update_task_checks_end_after_start_with_current_values():
    target = _make_task(1)
    service, repository, _ = _make_service([target])

    with pytest.raises(ValidationError) as exc_info:
        await service.update_task(
            1,
            TaskUpdate(done_flag=True, schedule=ScheduleUpdate(start_at=target.schedule.end_at)),
            _make_user(),
        )

    assert exc_info.value.details == [
        {"field": "schedule.end_at", "reason": "must_be_after_start_at"}
    ]
    assert target.done_flag is False
    assert repository.saved == []


@pytest.mark.anyio
async def test_service_delete_task_deletes_unactualized_planned_transactions_first():
    target = _make_task(1)
    service, repository, planned_transaction_repository = _make_service([target])

    await service.delete_task(1, _make_user())

    assert planned_transaction_repository.deleted_schedule_ids == [1]
    assert repository.deleted == [target]


@pytest.mark.anyio
async def test_service_delete_other_users_task_does_nothing():
    service, repository, planned_transaction_repository = _make_service(
        [_make_task(1, user_id=2)]
    )

    with pytest.raises(NotFoundError):
        await service.delete_task(1, _make_user(1))
    assert planned_transaction_repository.deleted_schedule_ids == []
    assert repository.deleted == []


# ---- Tasks API（DB使用） ----

def _at(day: int, hour: int) -> str:
    return datetime(2026, 9, day, hour, tzinfo=timezone(timedelta(hours=9))).isoformat()


def _create(client: TestClient, headers, due_date: str | None = None, **schedule) -> dict:
    payload = {
        "schedule": {
            "title": "レポート提出",
            "description": "確率論レポート",
            "start_at": _at(8, 18),
            "end_at": _at(8, 19),
            "category": "assignment",
            **schedule,
        },
        "due_date": due_date or _at(12, 23),
    }
    response = client.post("/api/v1/tasks", json=payload, headers=headers)
    assert response.status_code == 201, response.json()
    return response.json()


def _list_ids(client: TestClient, headers, **params) -> list[int]:
    response = client.get("/api/v1/tasks", params=params, headers=headers)
    assert response.status_code == 200, response.json()
    return [item["schedule_id"] for item in response.json()["items"]]


def test_task_crud(client: TestClient, authenticated_user):
    headers = authenticated_user["headers"]

    created = _create(client, headers)
    assert set(created) == {"schedule_id", "due_date", "done_flag", "schedule"}
    assert set(created["schedule"]) == {
        "id", "title", "description", "start_at", "end_at", "kind", "category",
        "google_sync_status", "created_at", "updated_at",
    }
    assert created["schedule_id"] == created["schedule"]["id"]
    assert created["done_flag"] is False
    assert created["schedule"]["kind"] == "task"
    assert created["schedule"]["title"] == "レポート提出"
    assert created["schedule"]["category"] == "assignment"
    # UTCで保存し、UTCで返す
    assert datetime.fromisoformat(created["due_date"]) == datetime.fromisoformat(_at(12, 23))
    assert datetime.fromisoformat(created["due_date"]).utcoffset() == timedelta(0)

    task_url = f"/api/v1/tasks/{created['schedule_id']}"
    response = client.get(task_url, headers=headers)
    assert response.status_code == 200
    assert response.json() == created

    # Schedules APIからも同じ予定として見える
    schedule = client.get(f"/api/v1/schedules/{created['schedule_id']}", headers=headers).json()
    assert schedule["kind"] == "task"
    assert schedule["task"] == {"due_date": created["due_date"], "done_flag": False}

    response = client.patch(
        task_url,
        json={
            "done_flag": True,
            "due_date": _at(13, 23),
            "schedule": {"title": "レポート提出済み", "description": None},
        },
        headers=headers,
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["done_flag"] is True
    assert datetime.fromisoformat(updated["due_date"]) == datetime.fromisoformat(_at(13, 23))
    assert updated["schedule"]["title"] == "レポート提出済み"
    assert updated["schedule"]["description"] is None
    assert updated["schedule"]["category"] == "assignment"
    assert updated["schedule"]["start_at"] == created["schedule"]["start_at"]
    assert client.get(task_url, headers=headers).json() == updated

    response = client.delete(task_url, headers=headers)
    assert response.status_code == 204
    assert client.get(task_url, headers=headers).status_code == 404
    assert client.get(
        f"/api/v1/schedules/{created['schedule_id']}", headers=headers
    ).status_code == 404


def test_update_only_task_fields(client: TestClient, authenticated_user):
    headers = authenticated_user["headers"]
    created = _create(client, headers)

    response = client.patch(
        f"/api/v1/tasks/{created['schedule_id']}",
        json={"done_flag": True},
        headers=headers,
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["done_flag"] is True
    assert updated["due_date"] == created["due_date"]
    assert updated["schedule"]["title"] == created["schedule"]["title"]


@pytest.mark.parametrize(
    ("payload", "field", "reason"),
    [
        ({"schedule": {"title": "", "start_at": _at(8, 18), "end_at": _at(8, 19)}},
         "schedule.title", "string_too_short"),
        ({"schedule": {"title": "a", "start_at": _at(8, 18), "end_at": _at(8, 18)}},
         "schedule.end_at", "must_be_after_start_at"),
        ({"schedule": {"title": "a", "start_at": _at(8, 18), "end_at": _at(8, 19)}},
         "due_date", "missing"),
        ({"schedule": {"title": "a", "start_at": _at(8, 18), "end_at": _at(8, 19)},
          "due_date": "2026-09-12T23:59:00"},
         "due_date", "timezone_aware"),
        ({"due_date": _at(12, 23)}, "schedule", "missing"),
    ],
)
def test_create_task_validation(client: TestClient, authenticated_user, payload, field, reason):
    response = client.post("/api/v1/tasks", json=payload, headers=authenticated_user["headers"])

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert {"field": field, "reason": reason} in error["details"]


def test_create_task_ignores_kind_and_done_flag(client: TestClient, authenticated_user):
    headers = authenticated_user["headers"]

    response = client.post(
        "/api/v1/tasks",
        json={
            "schedule": {
                "title": "a", "start_at": _at(8, 18), "end_at": _at(8, 19), "kind": "event",
            },
            "due_date": _at(12, 23),
            "done_flag": True,
        },
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["done_flag"] is False
    assert response.json()["schedule"]["kind"] == "task"


@pytest.mark.parametrize(
    ("payload", "field", "reason"),
    [
        ({"done_flag": None}, "done_flag", "not_nullable"),
        ({"due_date": None}, "due_date", "not_nullable"),
        ({"schedule": None}, "schedule", "not_nullable"),
        ({"schedule": {"title": None}}, "schedule.title", "not_nullable"),
        ({"schedule": {"kind": "event"}}, "schedule.kind", "extra_forbidden"),
        ({"schedule_id": 1}, "schedule_id", "extra_forbidden"),
        ({"schedule": {"end_at": _at(8, 18)}}, "schedule.end_at", "must_be_after_start_at"),
        ({"schedule": {"start_at": _at(8, 20)}}, "schedule.end_at", "must_be_after_start_at"),
    ],
)
def test_update_task_validation(client: TestClient, authenticated_user, payload, field, reason):
    headers = authenticated_user["headers"]
    created = _create(client, headers)
    task_url = f"/api/v1/tasks/{created['schedule_id']}"

    # 不正な項目と一緒に送った正しい項目も更新されない
    response = client.patch(task_url, json={"done_flag": True, **payload}, headers=headers)

    assert response.status_code == 422
    assert {"field": field, "reason": reason} in response.json()["error"]["details"]
    assert client.get(task_url, headers=headers).json() == created


def test_list_tasks_returns_tasks_in_due_order(client: TestClient, authenticated_user):
    headers = authenticated_user["headers"]
    late = _create(client, headers, due_date=_at(20, 0))
    early = _create(client, headers, due_date=_at(10, 0))
    middle = _create(client, headers, due_date=_at(15, 0))
    # kind=task以外の予定は含めない
    response = client.post(
        "/api/v1/schedules",
        json={"title": "ゼミ", "start_at": _at(10, 13), "end_at": _at(10, 15), "kind": "event"},
        headers=headers,
    )
    assert response.status_code == 201

    response = client.get("/api/v1/tasks", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert [item["schedule_id"] for item in body["items"]] == [
        early["schedule_id"], middle["schedule_id"], late["schedule_id"]
    ]
    assert body["next_cursor"] is None


def test_list_tasks_filters(client: TestClient, authenticated_user):
    headers = authenticated_user["headers"]
    first = _create(client, headers, due_date=_at(10, 0), category="assignment")
    second = _create(client, headers, due_date=_at(15, 0), category="private")
    third = _create(client, headers, due_date=_at(20, 0), category="assignment")
    client.patch(
        f"/api/v1/tasks/{second['schedule_id']}", json={"done_flag": True}, headers=headers
    )
    ids = [first["schedule_id"], second["schedule_id"], third["schedule_id"]]

    assert _list_ids(client, headers, done="false") == [ids[0], ids[2]]
    assert _list_ids(client, headers, done="true") == [ids[1]]
    assert _list_ids(client, headers, category="assignment") == [ids[0], ids[2]]
    # 期限の範囲は両端を含む
    assert _list_ids(client, headers, due_from=_at(15, 0)) == [ids[1], ids[2]]
    assert _list_ids(client, headers, due_to=_at(15, 0)) == [ids[0], ids[1]]
    assert _list_ids(client, headers, due_from=_at(11, 0), due_to=_at(19, 0)) == [ids[1]]
    assert _list_ids(client, headers, done="false", category="private") == []


def test_list_tasks_pagination(client: TestClient, authenticated_user):
    headers = authenticated_user["headers"]
    # 同じ期限のタスクはschedule_idの昇順で並べる
    created = [
        _create(client, headers, due_date=_at(10, 0)),
        _create(client, headers, due_date=_at(10, 0)),
        _create(client, headers, due_date=_at(5, 0)),
    ]
    expected = [created[2]["schedule_id"], created[0]["schedule_id"], created[1]["schedule_id"]]

    first = client.get("/api/v1/tasks", params={"limit": 2}, headers=headers).json()
    assert [item["schedule_id"] for item in first["items"]] == expected[:2]
    assert first["next_cursor"] == Cursor.encode(expected[1])

    second = client.get(
        "/api/v1/tasks", params={"limit": 2, "cursor": first["next_cursor"]}, headers=headers
    ).json()
    assert [item["schedule_id"] for item in second["items"]] == expected[2:]
    assert second["next_cursor"] is None


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"done": "maybe"}, "done"),
        ({"due_from": "2026-09-01T00:00:00"}, "due_from"),
        ({"due_from": _at(10, 0), "due_to": _at(9, 0)}, "due_to"),
        ({"cursor": Cursor.encode(999999)}, "cursor"),
    ],
)
def test_list_tasks_validation(client: TestClient, authenticated_user, params, field):
    response = client.get("/api/v1/tasks", params=params, headers=authenticated_user["headers"])

    assert response.status_code == 422
    assert field in [detail["field"] for detail in response.json()["error"]["details"]]


def test_tasks_require_authentication(client: TestClient):
    assert client.get("/api/v1/tasks").status_code == 401
    assert client.post("/api/v1/tasks", json={}).status_code == 401
    assert client.get("/api/v1/tasks/1").status_code == 401
    assert client.patch("/api/v1/tasks/1", json={}).status_code == 401
    assert client.delete("/api/v1/tasks/1").status_code == 401


def test_user_cannot_access_another_users_task(client: TestClient, auth_headers):
    owner_headers = auth_headers(sub="auth0|owner")
    other_headers = auth_headers(sub="auth0|other")
    created = _create(client, owner_headers)
    task_url = f"/api/v1/tasks/{created['schedule_id']}"

    assert client.get(task_url, headers=other_headers).status_code == 404
    assert client.patch(task_url, json={"done_flag": True}, headers=other_headers).status_code == 404
    assert client.delete(task_url, headers=other_headers).status_code == 404
    assert _list_ids(client, other_headers) == []
    # 他ユーザーのタスクをカーソルに使っても続きを取得できない
    response = client.get(
        "/api/v1/tasks",
        params={"cursor": Cursor.encode(created["schedule_id"])},
        headers=other_headers,
    )
    assert response.status_code == 422

    assert client.get(task_url, headers=owner_headers).json() == created


def test_tasks_api_does_not_return_non_task_schedule(client: TestClient, authenticated_user):
    headers = authenticated_user["headers"]
    response = client.post(
        "/api/v1/schedules",
        json={"title": "ゼミ", "start_at": _at(10, 13), "end_at": _at(10, 15), "kind": "event"},
        headers=headers,
    )
    schedule_id = response.json()["id"]

    assert client.get(f"/api/v1/tasks/{schedule_id}", headers=headers).status_code == 404
    assert client.patch(
        f"/api/v1/tasks/{schedule_id}", json={"done_flag": True}, headers=headers
    ).status_code == 404
    assert client.delete(f"/api/v1/tasks/{schedule_id}", headers=headers).status_code == 404
    assert client.get(f"/api/v1/schedules/{schedule_id}", headers=headers).status_code == 200


def test_create_task_rolls_back_schedule_when_task_insert_fails(
        client: TestClient, authenticated_user, migrated_engine
):
    headers = authenticated_user["headers"]
    # Taskの保存だけが失敗するよう、tasksテーブルに常に失敗する制約を付ける
    with migrated_engine.begin() as connection:
        connection.execute(text(
            "ALTER TABLE tasks ADD CONSTRAINT ck_tasks_test_always_fail CHECK (false) NOT VALID"
        ))

    with pytest.raises(Exception):
        client.post(
            "/api/v1/tasks",
            json={
                "schedule": {"title": "a", "start_at": _at(8, 18), "end_at": _at(8, 19)},
                "due_date": _at(12, 23),
            },
            headers=headers,
        )

    with migrated_engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM schedules")) == 0
        assert connection.scalar(text("SELECT count(*) FROM tasks")) == 0


def test_delete_task_handles_planned_transactions(
        client: TestClient, authenticated_user, migrated_engine
):
    headers = authenticated_user["headers"]
    user_id = client.get("/api/v1/users/me", headers=headers).json()["id"]
    target = _create(client, headers)

    with migrated_engine.begin() as connection:
        account_id = connection.scalar(
            text(
                "INSERT INTO accounts (user_id, name, type) "
                "VALUES (:user_id, '財布', 'cash') RETURNING id"
            ),
            {"user_id": user_id},
        )

        def add_planned() -> int:
            return connection.scalar(
                text(
                    "INSERT INTO planned_transactions "
                    "(user_id, schedule_id, account_id, type, amount, expected_date) "
                    "VALUES (:user_id, :schedule_id, :account_id, 'expense', 1000, '2026-09-25') "
                    "RETURNING id"
                ),
                {"user_id": user_id, "schedule_id": target["schedule_id"], "account_id": account_id},
            )

        unactualized_id = add_planned()
        actualized_id = add_planned()
        connection.execute(
            text(
                "INSERT INTO transactions "
                "(user_id, account_id, planned_transaction_id, type, amount, source, occurred_at) "
                "VALUES (:user_id, :account_id, :planned_id, 'expense', 1000, 'schedule', now())"
            ),
            {"user_id": user_id, "account_id": account_id, "planned_id": actualized_id},
        )

    response = client.delete(f"/api/v1/tasks/{target['schedule_id']}", headers=headers)
    assert response.status_code == 204

    with migrated_engine.connect() as connection:
        planned = dict(connection.execute(
            text("SELECT id, schedule_id FROM planned_transactions")
        ).all())
        # 未実績化の見込は削除され、実績化済みの見込は予定との関連だけが外れて残る
        assert planned == {actualized_id: None}
        assert unactualized_id not in planned
        assert connection.scalar(text("SELECT count(*) FROM schedules")) == 0
        assert connection.scalar(text("SELECT count(*) FROM tasks")) == 0
