from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.errors import NotFoundError, ValidationError
from app.core.pagination import Cursor, PageParams
from app.models.auth import User
from app.models.schedule import Schedule
from app.schemas.schedule import ScheduleCreate, ScheduleListParams, ScheduleUpdate
from app.services.schedule import ScheduleService

BASE_AT = datetime(2026, 9, 10, 4, 0, tzinfo=timezone.utc)


# ---- ScheduleService（DB不要） ----

class FakeScheduleRepository:
    def __init__(self, schedules: list[Schedule] | None = None):
        self.schedules = schedules or []
        self.saved: list[Schedule] = []
        self.deleted: list[Schedule] = []
        self.list_calls: list[dict] = []

    async def get_by_id(self, schedule_id: int, owner_id: int) -> Schedule | None:
        return next(
            (s for s in self.schedules if s.id == schedule_id and s.user_id == owner_id),
            None,
        )

    async def list_page_in_period(self, owner_id, from_at, to_at, limit, **filters):
        self.list_calls.append({"owner_id": owner_id, "limit": limit, **filters})
        return [s for s in self.schedules if s.user_id == owner_id][:limit + 1]

    async def add(self, schedule: Schedule) -> Schedule:
        schedule.id = len(self.schedules) + 1
        schedule.created_at = schedule.updated_at = BASE_AT
        self.schedules.append(schedule)
        return schedule

    async def save(self, schedule: Schedule) -> Schedule:
        self.saved.append(schedule)
        return schedule

    async def delete(self, schedule: Schedule) -> None:
        self.deleted.append(schedule)


class FakePlannedTransactionRepository:
    def __init__(self):
        self.deleted_schedule_ids: list[int] = []

    async def delete_unactualized_by_schedule(self, schedule_id: int) -> None:
        self.deleted_schedule_ids.append(schedule_id)


def _make_user(user_id: int = 1) -> User:
    return User(id=user_id, username=f"user{user_id}", auth_subject=f"auth0|user{user_id}")


def _make_schedule(schedule_id: int, user_id: int = 1, hours: int = 0) -> Schedule:
    return Schedule(
        id=schedule_id,
        user_id=user_id,
        title=f"schedule{schedule_id}",
        description=None,
        start_at=BASE_AT + timedelta(hours=hours),
        end_at=BASE_AT + timedelta(hours=hours + 1),
        kind="event",
        category=None,
        task=None,
        shift=None,
        created_at=BASE_AT,
        updated_at=BASE_AT,
    )


def _make_service(schedules: list[Schedule] | None = None):
    repository = FakeScheduleRepository(schedules)
    planned_transaction_repository = FakePlannedTransactionRepository()
    return (
        ScheduleService(repository, planned_transaction_repository),
        repository,
        planned_transaction_repository,
    )


def _list_params(**overrides) -> ScheduleListParams:
    values = {"from_at": BASE_AT, "to_at": BASE_AT + timedelta(days=1)}
    values.update(overrides)
    return ScheduleListParams(**values)


@pytest.mark.anyio
async def test_service_create_schedule_sets_owner():
    service, repository, _ = _make_service()

    response = await service.create_schedule(
        ScheduleCreate(
            title="ゼミ",
            start_at=BASE_AT,
            end_at=BASE_AT + timedelta(hours=1),
            kind="event",
        ),
        _make_user(7),
    )

    assert repository.schedules[0].user_id == 7
    assert response.kind == "event"
    assert response.google_sync_status == "not_connected"
    assert response.task is None and response.shift is None


@pytest.mark.anyio
async def test_service_get_other_users_schedule_raises_not_found():
    service, _, _ = _make_service([_make_schedule(1, user_id=2)])

    with pytest.raises(NotFoundError):
        await service.get_schedule(1, _make_user(1))


@pytest.mark.anyio
async def test_service_list_schedules_builds_next_cursor():
    schedules = [_make_schedule(i, hours=i) for i in range(1, 4)]
    service, repository, _ = _make_service(schedules)

    page = await service.list_schedules(
        _list_params(kinds=["event"], category="class"),
        PageParams(limit=2),
        _make_user(),
    )

    assert [item.id for item in page.items] == [1, 2]
    assert page.next_cursor == Cursor.encode(2)
    assert repository.list_calls[0]["kinds"] == ["event"]
    assert repository.list_calls[0]["category"] == "class"
    assert repository.list_calls[0]["after"] is None


@pytest.mark.anyio
async def test_service_list_schedules_continues_after_cursor_schedule():
    after = _make_schedule(5)
    service, repository, _ = _make_service([after])

    await service.list_schedules(_list_params(), PageParams(after_id=5), _make_user())

    assert repository.list_calls[0]["after"] is after


@pytest.mark.anyio
async def test_service_list_schedules_with_unknown_cursor_raises_validation_error():
    service, _, _ = _make_service([_make_schedule(5, user_id=2)])

    with pytest.raises(ValidationError):
        await service.list_schedules(_list_params(), PageParams(after_id=5), _make_user(1))


@pytest.mark.anyio
async def test_service_update_schedule_changes_only_given_fields():
    target = _make_schedule(1)
    target.description = "keep"
    service, repository, _ = _make_service([target])

    response = await service.update_schedule(
        1,
        ScheduleUpdate(title="changed", category=None),
        _make_user(),
    )

    assert response.title == "changed"
    assert response.description == "keep"
    assert response.category is None
    assert repository.saved == [target]


@pytest.mark.anyio
async def test_service_update_schedule_checks_end_after_start_with_current_values():
    target = _make_schedule(1)
    service, repository, _ = _make_service([target])

    with pytest.raises(ValidationError) as exc_info:
        await service.update_schedule(
            1,
            ScheduleUpdate(start_at=target.end_at),
            _make_user(),
        )

    assert exc_info.value.details == [{"field": "end_at", "reason": "must_be_after_start_at"}]
    assert repository.saved == []


@pytest.mark.anyio
async def test_service_delete_schedule_deletes_unactualized_planned_transactions_first():
    target = _make_schedule(1)
    service, repository, planned_transaction_repository = _make_service([target])

    await service.delete_schedule(1, _make_user())

    assert planned_transaction_repository.deleted_schedule_ids == [1]
    assert repository.deleted == [target]


@pytest.mark.anyio
async def test_service_delete_other_users_schedule_does_nothing():
    service, repository, planned_transaction_repository = _make_service(
        [_make_schedule(1, user_id=2)]
    )

    with pytest.raises(NotFoundError):
        await service.delete_schedule(1, _make_user(1))
    assert planned_transaction_repository.deleted_schedule_ids == []
    assert repository.deleted == []


# ---- Schedules API（DB使用） ----

def _at(day: int, hour: int) -> str:
    return datetime(2026, 9, day, hour, tzinfo=timezone(timedelta(hours=9))).isoformat()


def _create(client: TestClient, headers, **overrides) -> dict:
    payload = {
        "title": "ゼミ",
        "description": "進捗発表",
        "start_at": _at(10, 13),
        "end_at": _at(10, 15),
        "kind": "event",
        "category": "class",
    }
    payload.update(overrides)
    response = client.post("/api/v1/schedules", json=payload, headers=headers)
    assert response.status_code == 201, response.json()
    return response.json()


def _list(client: TestClient, headers, **params):
    query = {"from": _at(1, 0), "to": _at(30, 0)}
    query.update(params)
    return client.get("/api/v1/schedules", params=query, headers=headers)


def test_schedule_crud(client: TestClient, authenticated_user):
    headers = authenticated_user["headers"]

    created = _create(client, headers)
    assert set(created) == {
        "id", "title", "description", "start_at", "end_at", "kind", "category",
        "task", "shift", "google_sync_status", "created_at", "updated_at",
    }
    assert created["title"] == "ゼミ"
    assert created["kind"] == "event"
    assert created["task"] is None and created["shift"] is None
    assert created["google_sync_status"] == "not_connected"
    # UTCで保存し、UTCで返す
    assert datetime.fromisoformat(created["start_at"]) == datetime.fromisoformat(_at(10, 13))
    assert datetime.fromisoformat(created["start_at"]).utcoffset() == timedelta(0)

    schedule_url = f"/api/v1/schedules/{created['id']}"
    response = client.get(schedule_url, headers=headers)
    assert response.status_code == 200
    assert response.json() == created

    response = client.patch(
        schedule_url,
        json={"title": "ゼミ（教室変更）", "start_at": _at(10, 14), "description": None},
        headers=headers,
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["title"] == "ゼミ（教室変更）"
    assert datetime.fromisoformat(updated["start_at"]) == datetime.fromisoformat(_at(10, 14))
    assert updated["end_at"] == created["end_at"]
    assert updated["description"] is None
    assert updated["category"] == "class"
    assert updated["kind"] == "event"

    response = client.delete(schedule_url, headers=headers)
    assert response.status_code == 204
    assert client.get(schedule_url, headers=headers).status_code == 404


def test_create_payment_schedule(client: TestClient, authenticated_user):
    created = _create(
        client,
        authenticated_user["headers"],
        kind="payment",
        category="rent",
        description=None,
    )

    assert created["kind"] == "payment"
    assert created["description"] is None


@pytest.mark.parametrize(
    ("overrides", "field", "reason"),
    [
        ({"kind": "task"}, "kind", "literal_error"),
        ({"kind": "shift"}, "kind", "literal_error"),
        ({"title": ""}, "title", "string_too_short"),
        ({"title": "   "}, "title", "string_too_short"),
        ({"title": "a" * 201}, "title", "string_too_long"),
        ({"description": "a" * 2001}, "description", "string_too_long"),
        ({"end_at": _at(10, 13)}, "end_at", "must_be_after_start_at"),
        ({"end_at": _at(10, 12)}, "end_at", "must_be_after_start_at"),
        ({"start_at": "2026-09-10T13:00:00"}, "start_at", "timezone_aware"),
    ],
)
def test_create_schedule_validation(
        client: TestClient, authenticated_user, overrides, field, reason
):
    payload = {
        "title": "ゼミ",
        "start_at": _at(10, 13),
        "end_at": _at(10, 15),
        "kind": "event",
    }
    payload.update(overrides)

    response = client.post(
        "/api/v1/schedules",
        json=payload,
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert {"field": field, "reason": reason} in error["details"]


def test_title_boundary_lengths(client: TestClient, authenticated_user):
    headers = authenticated_user["headers"]

    assert _create(client, headers, title="a")["title"] == "a"
    assert _create(client, headers, title="a" * 200, description="a" * 2000)["title"] == "a" * 200


@pytest.mark.parametrize(
    ("payload", "field", "reason"),
    [
        ({"kind": "payment"}, "kind", "extra_forbidden"),
        ({"title": None}, "title", "not_nullable"),
        ({"start_at": None}, "start_at", "not_nullable"),
        ({"title": ""}, "title", "string_too_short"),
        ({"end_at": _at(10, 13)}, "end_at", "must_be_after_start_at"),
        ({"start_at": _at(10, 16)}, "end_at", "must_be_after_start_at"),
    ],
)
def test_update_schedule_validation(
        client: TestClient, authenticated_user, payload, field, reason
):
    headers = authenticated_user["headers"]
    created = _create(client, headers)

    response = client.patch(
        f"/api/v1/schedules/{created['id']}",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 422
    assert {"field": field, "reason": reason} in response.json()["error"]["details"]
    assert client.get(f"/api/v1/schedules/{created['id']}", headers=headers).json() == created


def test_list_schedules_returns_overlapping_schedules_in_start_order(
        client: TestClient, authenticated_user
):
    headers = authenticated_user["headers"]
    inside_late = _create(client, headers, title="inside late", start_at=_at(20, 9), end_at=_at(20, 10))
    inside_early = _create(client, headers, title="inside early", start_at=_at(10, 9), end_at=_at(10, 10))
    overlap_start = _create(client, headers, title="overlap start", start_at=_at(9, 22), end_at=_at(10, 1))
    _create(client, headers, title="before", start_at=_at(9, 20), end_at=_at(10, 0))
    _create(client, headers, title="after", start_at=_at(25, 0), end_at=_at(25, 1))

    response = _list(client, headers, **{"from": _at(10, 0), "to": _at(25, 0)})

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["items"]] == [
        overlap_start["id"], inside_early["id"], inside_late["id"]
    ]
    assert body["next_cursor"] is None


def test_list_schedules_includes_schedule_covering_whole_period(
        client: TestClient, authenticated_user
):
    headers = authenticated_user["headers"]
    covering = _create(client, headers, start_at=_at(1, 0), end_at=_at(30, 0))

    response = _list(client, headers, **{"from": _at(10, 0), "to": _at(11, 0)})

    assert [item["id"] for item in response.json()["items"]] == [covering["id"]]


def test_list_schedules_filters_by_kind_and_category(client: TestClient, authenticated_user):
    headers = authenticated_user["headers"]
    event = _create(client, headers, kind="event", category="class")
    payment = _create(client, headers, kind="payment", category="rent")
    private = _create(client, headers, kind="event", category="private")

    def ids(**params):
        return [item["id"] for item in _list(client, headers, **params).json()["items"]]

    assert ids(kind="payment") == [payment["id"]]
    assert ids(kind=["event", "payment"]) == [event["id"], payment["id"], private["id"]]
    assert ids(category="private") == [private["id"]]
    assert ids(kind="event", category="class") == [event["id"]]
    assert ids(kind="task") == []


def test_list_schedules_pagination(client: TestClient, authenticated_user):
    headers = authenticated_user["headers"]
    # 同じ start_at の予定はIDの昇順で並べる
    created = [
        _create(client, headers, start_at=_at(10, 9), end_at=_at(10, 10)),
        _create(client, headers, start_at=_at(10, 9), end_at=_at(10, 11)),
        _create(client, headers, start_at=_at(5, 9), end_at=_at(5, 10)),
    ]
    expected = [created[2]["id"], created[0]["id"], created[1]["id"]]

    first = _list(client, headers, limit=2).json()
    assert [item["id"] for item in first["items"]] == expected[:2]
    assert first["next_cursor"] is not None

    second = _list(client, headers, limit=2, cursor=first["next_cursor"]).json()
    assert [item["id"] for item in second["items"]] == expected[2:]
    assert second["next_cursor"] is None


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"from": None}, "from"),
        ({"to": None}, "to"),
        ({"from": "2026-09-01T00:00:00"}, "from"),
        ({"to": "2026-08-01T00:00:00+09:00"}, "to"),
        ({"kind": "unknown"}, "kind.0"),
        ({"cursor": Cursor.encode(999999)}, "cursor"),
    ],
)
def test_list_schedules_validation(client: TestClient, authenticated_user, params, field):
    query = {"from": _at(1, 0), "to": _at(30, 0)}
    query.update(params)
    query = {key: value for key, value in query.items() if value is not None}

    response = client.get("/api/v1/schedules", params=query, headers=authenticated_user["headers"])

    assert response.status_code == 422
    assert field in [detail["field"] for detail in response.json()["error"]["details"]]


def test_schedules_require_authentication(client: TestClient):
    assert client.get("/api/v1/schedules", params={"from": _at(1, 0), "to": _at(30, 0)}).status_code == 401
    assert client.post("/api/v1/schedules", json={}).status_code == 401
    assert client.get("/api/v1/schedules/1").status_code == 401
    assert client.patch("/api/v1/schedules/1", json={}).status_code == 401
    assert client.delete("/api/v1/schedules/1").status_code == 401


def test_user_cannot_access_another_users_schedule(client: TestClient, auth_headers):
    owner_headers = auth_headers(sub="auth0|owner")
    other_headers = auth_headers(sub="auth0|other")
    created = _create(client, owner_headers)
    schedule_url = f"/api/v1/schedules/{created['id']}"

    assert client.get(schedule_url, headers=other_headers).status_code == 404
    assert client.patch(schedule_url, json={"title": "x"}, headers=other_headers).status_code == 404
    assert client.delete(schedule_url, headers=other_headers).status_code == 404
    assert _list(client, other_headers).json()["items"] == []
    # 他ユーザーの予定IDをカーソルに使っても続きを取得できない
    response = _list(client, other_headers, cursor=Cursor.encode(created["id"]))
    assert response.status_code == 422

    assert client.get(schedule_url, headers=owner_headers).json() == created


def test_get_task_schedule_includes_task_detail(client: TestClient, authenticated_user):
    headers = authenticated_user["headers"]
    task = client.post(
        "/api/v1/tasks",
        json={"title": "レポート", "description": "", "limit": "2026-09-12"},
        headers=headers,
    ).json()

    schedule = client.get(f"/api/v1/schedules/{task['id']}", headers=headers).json()

    assert schedule["kind"] == "task"
    assert schedule["shift"] is None
    assert schedule["task"]["done_flag"] is False
    assert datetime.fromisoformat(schedule["task"]["due_date"]) == datetime(
        2026, 9, 12, tzinfo=timezone.utc
    )

    response = client.patch(
        f"/api/v1/schedules/{task['id']}",
        json={"title": "レポート（再提出）"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["task"] == schedule["task"]


def test_get_shift_schedule_includes_shift_detail(
        client: TestClient, authenticated_user, migrated_engine
):
    headers = authenticated_user["headers"]
    created = _create(client, headers)
    # Shifts APIは未実装のため、kind=shiftの予定はDBに直接作る
    with migrated_engine.begin() as connection:
        connection.execute(
            text("UPDATE schedules SET kind = 'shift' WHERE id = :id"),
            {"id": created["id"]},
        )
        connection.execute(
            text(
                "INSERT INTO shifts (schedule_id, hourly_wage, break_minutes, workplace) "
                "VALUES (:id, 1300, 60, '新宿店')"
            ),
            {"id": created["id"]},
        )

    schedule = client.get(f"/api/v1/schedules/{created['id']}", headers=headers).json()

    assert schedule["kind"] == "shift"
    assert schedule["task"] is None
    assert schedule["shift"] == {"hourly_wage": 1300, "break_minutes": 60, "workplace": "新宿店"}

    response = client.delete(f"/api/v1/schedules/{created['id']}", headers=headers)
    assert response.status_code == 204
    with migrated_engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM shifts")) == 0


def test_delete_task_schedule_deletes_task(
        client: TestClient, authenticated_user, migrated_engine
):
    headers = authenticated_user["headers"]
    task = client.post(
        "/api/v1/tasks",
        json={"title": "レポート", "description": "", "limit": "2026-09-12"},
        headers=headers,
    ).json()

    assert client.delete(f"/api/v1/schedules/{task['id']}", headers=headers).status_code == 204
    assert client.get(f"/api/v1/tasks/{task['id']}", headers=headers).status_code == 404
    with migrated_engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM tasks")) == 0


def test_delete_schedule_handles_planned_transactions(
        client: TestClient, authenticated_user, migrated_engine
):
    headers = authenticated_user["headers"]
    user_id = client.get("/api/v1/users/me", headers=headers).json()["id"]
    target = _create(client, headers, kind="payment")
    other = _create(client, headers, kind="payment")

    with migrated_engine.begin() as connection:
        account_id = connection.scalar(
            text(
                "INSERT INTO accounts (user_id, name, type) "
                "VALUES (:user_id, '財布', 'cash') RETURNING id"
            ),
            {"user_id": user_id},
        )

        def add_planned(schedule_id: int) -> int:
            return connection.scalar(
                text(
                    "INSERT INTO planned_transactions "
                    "(user_id, schedule_id, account_id, type, amount, expected_date) "
                    "VALUES (:user_id, :schedule_id, :account_id, 'expense', 1000, '2026-09-25') "
                    "RETURNING id"
                ),
                {"user_id": user_id, "schedule_id": schedule_id, "account_id": account_id},
            )

        unactualized_id = add_planned(target["id"])
        actualized_id = add_planned(target["id"])
        other_schedule_planned_id = add_planned(other["id"])
        transaction_id = connection.scalar(
            text(
                "INSERT INTO transactions "
                "(user_id, account_id, planned_transaction_id, type, amount, source, occurred_at) "
                "VALUES (:user_id, :account_id, :planned_id, 'expense', 1000, 'schedule', now()) "
                "RETURNING id"
            ),
            {"user_id": user_id, "account_id": account_id, "planned_id": actualized_id},
        )

    response = client.delete(f"/api/v1/schedules/{target['id']}", headers=headers)
    assert response.status_code == 204

    with migrated_engine.connect() as connection:
        planned = dict(connection.execute(
            text("SELECT id, schedule_id FROM planned_transactions")
        ).all())
        # 未実績化の見込は削除され、実績化済みの見込は予定との関連だけが外れて残る
        assert planned == {actualized_id: None, other_schedule_planned_id: other["id"]}
        assert unactualized_id not in planned
        assert connection.scalar(
            text("SELECT planned_transaction_id FROM transactions WHERE id = :id"),
            {"id": transaction_id},
        ) == actualized_id
