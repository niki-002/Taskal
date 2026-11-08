from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import text

from app.core.errors import NotFoundError, ValidationError
from app.core.pagination import Cursor, PageParams
from app.models.auth import User
from app.models.schedule import Schedule
from app.models.shift import Shift
from app.schemas.schedule import ScheduleBaseCreate, ScheduleBaseResponse, ScheduleUpdate
from app.schemas.shift import ShiftCreate, ShiftListParams, ShiftResponse, ShiftUpdate
from app.services.shift import ShiftService

BASE_AT = datetime(2026, 9, 15, 1, 0, tzinfo=timezone.utc)


# ---- ShiftService（DB不要） ----

class FakeShiftRepository:
    def __init__(self, shifts: list[Shift] | None = None):
        self.shifts = shifts or []
        self.saved: list[Shift] = []
        self.deleted: list[Shift] = []
        self.list_calls: list[dict] = []

    async def get_by_id(self, schedule_id: int, owner_id: int) -> Shift | None:
        return next(
            (
                s for s in self.shifts
                if s.schedule_id == schedule_id and s.schedule.user_id == owner_id
            ),
            None,
        )

    async def list_page_in_period(self, owner_id, from_at, to_at, limit, after=None):
        self.list_calls.append({
            "owner_id": owner_id,
            "from_at": from_at,
            "to_at": to_at,
            "limit": limit,
            "after": after,
        })
        return [s for s in self.shifts if s.schedule.user_id == owner_id][:limit + 1]

    async def add(self, shift: Shift) -> Shift:
        shift.schedule.id = shift.schedule_id = len(self.shifts) + 1
        shift.schedule.created_at = shift.schedule.updated_at = BASE_AT
        self.shifts.append(shift)
        return shift

    async def save(self, shift: Shift) -> Shift:
        self.saved.append(shift)
        return shift

    async def delete(self, shift: Shift) -> None:
        self.deleted.append(shift)


class FakePlannedTransactionRepository:
    def __init__(self):
        self.deleted_schedule_ids: list[int] = []

    async def delete_unactualized_by_schedule(self, schedule_id: int) -> None:
        self.deleted_schedule_ids.append(schedule_id)


def _make_user(user_id: int = 1) -> User:
    return User(id=user_id, username=f"user{user_id}", auth_subject=f"auth0|user{user_id}")


def _make_shift(schedule_id: int, user_id: int = 1, hours: int = 8) -> Shift:
    return Shift(
        schedule_id=schedule_id,
        hourly_wage=1300,
        break_minutes=60,
        workplace="新宿店",
        schedule=Schedule(
            id=schedule_id,
            user_id=user_id,
            title=f"shift{schedule_id}",
            description=None,
            start_at=BASE_AT,
            end_at=BASE_AT + timedelta(hours=hours),
            kind="shift",
            category=None,
            created_at=BASE_AT,
            updated_at=BASE_AT,
        ),
    )


def _make_service(shifts: list[Shift] | None = None):
    repository = FakeShiftRepository(shifts)
    planned_transaction_repository = FakePlannedTransactionRepository()
    return (
        ShiftService(repository, planned_transaction_repository),
        repository,
        planned_transaction_repository,
    )


def _schedule_create(hours: int = 8) -> ScheduleBaseCreate:
    return ScheduleBaseCreate(
        title="カフェ勤務",
        start_at=BASE_AT,
        end_at=BASE_AT + timedelta(hours=hours),
    )


@pytest.mark.parametrize(
    ("working_time", "break_minutes", "hourly_wage", "expected"),
    [
        (timedelta(hours=8), 60, 1300, 9100),
        (timedelta(hours=8), 0, 1300, 10400),
        # 端数は四捨五入せず切り捨てる
        (timedelta(minutes=50), 0, 1000, 833),  # 833.33...
        (timedelta(minutes=100), 0, 1000, 1666),  # 1666.66...
        (timedelta(minutes=1), 0, 59, 0),  # 0.98...
        (timedelta(minutes=7), 0, 1111, 129),  # 129.61...
        # 勤務時間は分単位で計算し、1分未満は切り捨てる
        (timedelta(seconds=30), 0, 1200, 0),
        (timedelta(minutes=59, seconds=59), 0, 1200, 1180),
        # 時給が上限の大きな値でも切り捨てる
        (timedelta(days=3650, minutes=-1), 0, 2_147_483_647, 188119531685805),
        # 休憩時間と勤務時間が同じなら0円
        (timedelta(hours=1), 60, 1300, 0),
        (timedelta(hours=8), 60, 0, 0),
    ],
)
def test_estimated_income_truncates_fraction(working_time, break_minutes, hourly_wage, expected):
    response = ShiftResponse(
        schedule_id=1,
        hourly_wage=hourly_wage,
        break_minutes=break_minutes,
        workplace=None,
        schedule=ScheduleBaseResponse(
            id=1,
            title="カフェ勤務",
            description=None,
            start_at=BASE_AT,
            end_at=BASE_AT + working_time,
            kind="shift",
            category=None,
            created_at=BASE_AT,
            updated_at=BASE_AT,
        ),
    )

    assert response.estimated_income == expected


@pytest.mark.anyio
async def test_service_create_shift_sets_kind_and_owner():
    service, repository, _ = _make_service()

    response = await service.create_shift(
        ShiftCreate(
            schedule=_schedule_create(),
            hourly_wage=1300,
            break_minutes=60,
            workplace="新宿店",
        ),
        _make_user(7),
    )

    created = repository.shifts[0]
    assert created.schedule.user_id == 7
    assert created.schedule.kind == "shift"
    assert created.hourly_wage == 1300
    assert response.schedule_id == response.schedule.id == 1
    assert response.schedule.kind == "shift"
    assert response.workplace == "新宿店"
    assert response.estimated_income == 9100


def test_shift_create_break_minutes_defaults_to_zero():
    new_shift = ShiftCreate(schedule=_schedule_create(), hourly_wage=1300)

    assert new_shift.break_minutes == 0
    assert new_shift.workplace is None


def test_shift_create_rejects_break_longer_than_working_time():
    with pytest.raises(PydanticValidationError) as exc_info:
        ShiftCreate(schedule=_schedule_create(hours=1), hourly_wage=1300, break_minutes=61)

    error = exc_info.value.errors()[0]
    assert error["loc"] == ("break_minutes",)
    assert error["type"] == "exceeds_working_time"


@pytest.mark.anyio
async def test_service_get_other_users_shift_raises_not_found():
    service, _, _ = _make_service([_make_shift(1, user_id=2)])

    with pytest.raises(NotFoundError):
        await service.get_shift(1, _make_user(1))


@pytest.mark.anyio
async def test_service_list_shifts_passes_period_and_builds_next_cursor():
    shifts = [_make_shift(i) for i in range(1, 4)]
    service, repository, _ = _make_service(shifts)
    to_at = BASE_AT + timedelta(days=1)

    page = await service.list_shifts(
        ShiftListParams(from_at=BASE_AT, to_at=to_at),
        PageParams(limit=2),
        _make_user(),
    )

    assert [item.schedule_id for item in page.items] == [1, 2]
    assert page.next_cursor == Cursor.encode(2)
    assert repository.list_calls == [
        {"owner_id": 1, "from_at": BASE_AT, "to_at": to_at, "limit": 2, "after": None}
    ]


@pytest.mark.anyio
async def test_service_list_shifts_continues_after_cursor_shift():
    after = _make_shift(5)
    service, repository, _ = _make_service([after])

    await service.list_shifts(
        ShiftListParams(from_at=BASE_AT, to_at=BASE_AT + timedelta(days=1)),
        PageParams(after_id=5),
        _make_user(),
    )

    assert repository.list_calls[0]["after"] is after


@pytest.mark.anyio
async def test_service_list_shifts_with_unknown_cursor_raises_validation_error():
    service, _, _ = _make_service([_make_shift(5, user_id=2)])

    with pytest.raises(ValidationError):
        await service.list_shifts(
            ShiftListParams(from_at=BASE_AT, to_at=BASE_AT + timedelta(days=1)),
            PageParams(after_id=5),
            _make_user(1),
        )


@pytest.mark.anyio
async def test_service_update_shift_changes_shift_and_schedule_fields():
    target = _make_shift(1)
    target.schedule.description = "keep"
    service, repository, _ = _make_service([target])

    response = await service.update_shift(
        1,
        ShiftUpdate(
            hourly_wage=1350,
            workplace=None,
            schedule=ScheduleUpdate(title="カフェ勤務（延長）", category=None),
        ),
        _make_user(),
    )

    assert response.hourly_wage == 1350
    assert response.break_minutes == 60
    assert response.workplace is None
    assert response.schedule.title == "カフェ勤務（延長）"
    assert response.schedule.description == "keep"
    assert response.estimated_income == 9450
    assert repository.saved == [target]


@pytest.mark.anyio
async def test_service_update_shift_checks_end_after_start_with_current_values():
    target = _make_shift(1)
    service, repository, _ = _make_service([target])

    with pytest.raises(ValidationError) as exc_info:
        await service.update_shift(
            1,
            ShiftUpdate(hourly_wage=1, schedule=ScheduleUpdate(start_at=target.schedule.end_at)),
            _make_user(),
        )

    assert exc_info.value.details == [
        {"field": "schedule.end_at", "reason": "must_be_after_start_at"}
    ]
    assert target.hourly_wage == 1300
    assert repository.saved == []


@pytest.mark.parametrize(
    "new_data",
    [
        # 休憩時間だけを伸ばす
        ShiftUpdate(break_minutes=481),
        # 勤務時間だけを縮める
        ShiftUpdate(schedule=ScheduleUpdate(end_at=BASE_AT + timedelta(minutes=59))),
        ShiftUpdate(schedule=ScheduleUpdate(start_at=BASE_AT + timedelta(hours=7, minutes=1))),
    ],
)
@pytest.mark.anyio
async def test_service_update_shift_checks_break_with_updated_values(new_data):
    target = _make_shift(1)
    service, repository, _ = _make_service([target])

    with pytest.raises(ValidationError) as exc_info:
        await service.update_shift(1, new_data, _make_user())

    assert exc_info.value.details == [
        {"field": "break_minutes", "reason": "exceeds_working_time"}
    ]
    assert target.break_minutes == 60
    assert target.schedule.start_at == BASE_AT
    assert target.schedule.end_at == BASE_AT + timedelta(hours=8)
    assert repository.saved == []


@pytest.mark.anyio
async def test_service_update_shift_allows_shrinking_time_and_break_together():
    target = _make_shift(1)
    service, _, _ = _make_service([target])

    response = await service.update_shift(
        1,
        ShiftUpdate(
            break_minutes=30,
            schedule=ScheduleUpdate(end_at=BASE_AT + timedelta(minutes=30)),
        ),
        _make_user(),
    )

    assert response.break_minutes == 30
    assert response.estimated_income == 0


@pytest.mark.anyio
async def test_service_delete_shift_deletes_unactualized_planned_transactions_first():
    target = _make_shift(1)
    service, repository, planned_transaction_repository = _make_service([target])

    await service.delete_shift(1, _make_user())

    assert planned_transaction_repository.deleted_schedule_ids == [1]
    assert repository.deleted == [target]


@pytest.mark.anyio
async def test_service_delete_other_users_shift_does_nothing():
    service, repository, planned_transaction_repository = _make_service(
        [_make_shift(1, user_id=2)]
    )

    with pytest.raises(NotFoundError):
        await service.delete_shift(1, _make_user(1))
    assert planned_transaction_repository.deleted_schedule_ids == []
    assert repository.deleted == []


# ---- Shifts API（DB使用） ----

def _at(day: int, hour: int, minute: int = 0) -> str:
    return datetime(2026, 9, day, hour, minute, tzinfo=timezone(timedelta(hours=9))).isoformat()


def _payload(day: int = 15, start: int = 10, end: int = 18, **overrides) -> dict:
    return {
        "schedule": {
            "title": "カフェ勤務",
            "description": None,
            "start_at": _at(day, start),
            "end_at": _at(day, end),
            "category": "part_time",
        },
        "hourly_wage": 1300,
        "break_minutes": 60,
        "workplace": "新宿店",
        **overrides,
    }


def _create(client: TestClient, headers, **kwargs) -> dict:
    response = client.post("/api/v1/shifts", json=_payload(**kwargs), headers=headers)
    assert response.status_code == 201, response.json()
    return response.json()


def _list_ids(client: TestClient, headers, **params) -> list[int]:
    query = {"from": _at(1, 0), "to": _at(30, 0), **params}
    response = client.get("/api/v1/shifts", params=query, headers=headers)
    assert response.status_code == 200, response.json()
    return [item["schedule_id"] for item in response.json()["items"]]


def test_shift_crud(client: TestClient, authenticated_user):
    headers = authenticated_user["headers"]

    created = _create(client, headers)
    assert set(created) == {
        "schedule_id", "hourly_wage", "break_minutes", "workplace",
        "estimated_income", "schedule",
    }
    assert set(created["schedule"]) == {
        "id", "title", "description", "start_at", "end_at", "kind", "category",
        "google_sync_status", "created_at", "updated_at",
    }
    assert created["schedule_id"] == created["schedule"]["id"]
    assert created["hourly_wage"] == 1300
    assert created["break_minutes"] == 60
    assert created["workplace"] == "新宿店"
    assert created["estimated_income"] == 9100
    assert created["schedule"]["kind"] == "shift"
    assert created["schedule"]["category"] == "part_time"

    shift_url = f"/api/v1/shifts/{created['schedule_id']}"
    response = client.get(shift_url, headers=headers)
    assert response.status_code == 200
    assert response.json() == created

    # Schedules APIからも同じ予定として見える
    schedule = client.get(f"/api/v1/schedules/{created['schedule_id']}", headers=headers).json()
    assert schedule["kind"] == "shift"
    assert schedule["task"] is None
    assert schedule["shift"] == {"hourly_wage": 1300, "break_minutes": 60, "workplace": "新宿店"}

    response = client.patch(
        shift_url,
        json={
            "hourly_wage": 1350,
            "workplace": None,
            "schedule": {"end_at": _at(15, 19)},
        },
        headers=headers,
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["hourly_wage"] == 1350
    assert updated["break_minutes"] == 60
    assert updated["workplace"] is None
    # (540分 - 60分) × 1350円 ÷ 60
    assert updated["estimated_income"] == 10800
    assert datetime.fromisoformat(updated["schedule"]["end_at"]) == datetime.fromisoformat(_at(15, 19))
    assert updated["schedule"]["start_at"] == created["schedule"]["start_at"]
    assert updated["schedule"]["title"] == "カフェ勤務"
    assert client.get(shift_url, headers=headers).json() == updated

    response = client.delete(shift_url, headers=headers)
    assert response.status_code == 204
    assert client.get(shift_url, headers=headers).status_code == 404
    assert client.get(
        f"/api/v1/schedules/{created['schedule_id']}", headers=headers
    ).status_code == 404


def test_estimated_income_is_truncated_in_response(client: TestClient, authenticated_user):
    headers = authenticated_user["headers"]

    created = _create(
        client, headers, start=10, end=11, hourly_wage=1000, break_minutes=10
    )

    # 50分 × 1000円 ÷ 60 = 833.33...
    assert created["estimated_income"] == 833


def test_create_shift_ignores_kind_and_estimated_income(client: TestClient, authenticated_user):
    headers = authenticated_user["headers"]
    payload = _payload(estimated_income=1)
    payload["schedule"]["kind"] = "event"

    response = client.post("/api/v1/shifts", json=payload, headers=headers)

    assert response.status_code == 201
    assert response.json()["schedule"]["kind"] == "shift"
    assert response.json()["estimated_income"] == 9100


def test_create_shift_with_only_required_fields(client: TestClient, authenticated_user):
    response = client.post(
        "/api/v1/shifts",
        json={
            "schedule": {"title": "a", "start_at": _at(15, 10), "end_at": _at(15, 11)},
            "hourly_wage": 0,
        },
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 201
    created = response.json()
    assert created["break_minutes"] == 0
    assert created["workplace"] is None
    assert created["estimated_income"] == 0


def test_create_shift_accepts_break_equal_to_working_time(client: TestClient, authenticated_user):
    created = _create(
        client, authenticated_user["headers"], start=10, end=11, break_minutes=60
    )

    assert created["estimated_income"] == 0


def test_create_shift_accepts_workplace_of_max_length(client: TestClient, authenticated_user):
    created = _create(client, authenticated_user["headers"], workplace="a" * 200)

    assert len(created["workplace"]) == 200


@pytest.mark.parametrize(
    ("overrides", "field", "reason"),
    [
        ({"hourly_wage": -1}, "hourly_wage", "greater_than_equal"),
        ({"hourly_wage": 1.5}, "hourly_wage", "int_from_float"),
        ({"hourly_wage": None}, "hourly_wage", "int_type"),
        # DBのINTEGERに入らない値は500にせず422で返す
        ({"hourly_wage": 2_147_483_648}, "hourly_wage", "less_than_equal"),
        ({"break_minutes": -1}, "break_minutes", "greater_than_equal"),
        ({"break_minutes": 1.5}, "break_minutes", "int_from_float"),
        ({"break_minutes": 2_147_483_648}, "break_minutes", "less_than_equal"),
        ({"break_minutes": 481}, "break_minutes", "exceeds_working_time"),
        ({"workplace": "a" * 201}, "workplace", "string_too_long"),
    ],
)
def test_create_shift_validation(
        client: TestClient, authenticated_user, overrides, field, reason
):
    response = client.post(
        "/api/v1/shifts",
        json=_payload(**overrides),
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"] == [{"field": field, "reason": reason}]


@pytest.mark.parametrize(
    ("schedule", "field", "reason"),
    [
        ({"title": " "}, "schedule.title", "string_too_short"),
        ({"end_at": _at(15, 10)}, "schedule.end_at", "must_be_after_start_at"),
        ({"start_at": "2026-09-15T10:00:00"}, "schedule.start_at", "timezone_aware"),
    ],
)
def test_create_shift_schedule_validation(
        client: TestClient, authenticated_user, schedule, field, reason
):
    payload = _payload()
    payload["schedule"].update(schedule)

    response = client.post(
        "/api/v1/shifts", json=payload, headers=authenticated_user["headers"]
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"] == [{"field": field, "reason": reason}]


@pytest.mark.parametrize(
    ("payload", "field", "reason"),
    [
        ({"hourly_wage": None}, "hourly_wage", "not_nullable"),
        ({"break_minutes": None}, "break_minutes", "not_nullable"),
        ({"schedule": None}, "schedule", "not_nullable"),
        ({"hourly_wage": -1}, "hourly_wage", "greater_than_equal"),
        ({"hourly_wage": 2_147_483_648}, "hourly_wage", "less_than_equal"),
        ({"break_minutes": -1}, "break_minutes", "greater_than_equal"),
        ({"workplace": "a" * 201}, "workplace", "string_too_long"),
        ({"break_minutes": 481}, "break_minutes", "exceeds_working_time"),
        ({"schedule": {"end_at": _at(15, 10, 59)}}, "break_minutes", "exceeds_working_time"),
        ({"schedule": {"end_at": _at(15, 10)}}, "schedule.end_at", "must_be_after_start_at"),
        ({"schedule": {"kind": "event"}}, "schedule.kind", "extra_forbidden"),
        ({"estimated_income": 1}, "estimated_income", "extra_forbidden"),
    ],
)
def test_update_shift_validation(client: TestClient, authenticated_user, payload, field, reason):
    headers = authenticated_user["headers"]
    created = _create(client, headers)

    response = client.patch(
        f"/api/v1/shifts/{created['schedule_id']}", json=payload, headers=headers
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"] == [{"field": field, "reason": reason}]
    assert client.get(
        f"/api/v1/shifts/{created['schedule_id']}", headers=headers
    ).json() == created


def test_schedule_patch_cannot_make_working_time_shorter_than_break(
        client: TestClient, authenticated_user
):
    headers = authenticated_user["headers"]
    created = _create(client, headers)
    schedule_url = f"/api/v1/schedules/{created['schedule_id']}"

    response = client.patch(schedule_url, json={"end_at": _at(15, 10, 59)}, headers=headers)

    assert response.status_code == 422
    assert response.json()["error"]["details"] == [
        {"field": "end_at", "reason": "exceeds_working_time"}
    ]

    # 休憩時間と同じ長さまでは縮められ、見込収入にも反映される
    response = client.patch(schedule_url, json={"end_at": _at(15, 11)}, headers=headers)
    assert response.status_code == 200
    assert client.get(
        f"/api/v1/shifts/{created['schedule_id']}", headers=headers
    ).json()["estimated_income"] == 0


def test_list_shifts_returns_shifts_in_start_order(client: TestClient, authenticated_user):
    headers = authenticated_user["headers"]
    later = _create(client, headers, day=20)
    earlier = _create(client, headers, day=10)
    same_start = _create(client, headers, day=10)

    assert _list_ids(client, headers) == [
        earlier["schedule_id"], same_start["schedule_id"], later["schedule_id"],
    ]


def test_list_shifts_filters_by_period(client: TestClient, authenticated_user):
    headers = authenticated_user["headers"]
    target = _create(client, headers, day=10, start=10, end=18)

    params = [
        ({"from": _at(10, 18), "to": _at(11, 0)}, []),  # end_at はfromと同時刻なら重ならない
        ({"from": _at(10, 0), "to": _at(10, 10)}, []),  # to は境界を含まない
        ({"from": _at(10, 17), "to": _at(11, 0)}, [target["schedule_id"]]),
        ({"from": _at(10, 0), "to": _at(10, 11)}, [target["schedule_id"]]),
        ({"from": _at(10, 12), "to": _at(10, 13)}, [target["schedule_id"]]),
    ]
    for query, expected in params:
        assert _list_ids(client, headers, **query) == expected


def test_list_shifts_pagination(client: TestClient, authenticated_user):
    headers = authenticated_user["headers"]
    expected = [_create(client, headers, day=day)["schedule_id"] for day in (5, 6, 7)]
    query = {"from": _at(1, 0), "to": _at(30, 0), "limit": 2}

    first = client.get("/api/v1/shifts", params=query, headers=headers).json()
    assert [item["schedule_id"] for item in first["items"]] == expected[:2]
    assert first["next_cursor"] is not None

    second = client.get(
        "/api/v1/shifts",
        params={**query, "cursor": first["next_cursor"]},
        headers=headers,
    ).json()
    assert [item["schedule_id"] for item in second["items"]] == expected[2:]
    assert second["next_cursor"] is None


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"to": _at(30, 0)}, "from"),
        ({"from": _at(1, 0)}, "to"),
        ({"from": _at(2, 0), "to": _at(2, 0)}, "to"),
        ({"from": "2026-09-01T00:00:00", "to": _at(30, 0)}, "from"),
        ({"from": _at(1, 0), "to": _at(30, 0), "cursor": "invalid"}, "cursor"),
        ({"from": _at(1, 0), "to": _at(30, 0), "cursor": Cursor.encode(999999)}, "cursor"),
        ({"from": _at(1, 0), "to": _at(30, 0), "limit": 0}, "limit"),
    ],
)
def test_list_shifts_validation(client: TestClient, authenticated_user, params, field):
    response = client.get(
        "/api/v1/shifts", params=params, headers=authenticated_user["headers"]
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == field


def test_shifts_require_authentication(client: TestClient):
    assert client.get("/api/v1/shifts").status_code == 401
    assert client.post("/api/v1/shifts", json=_payload()).status_code == 401
    assert client.get("/api/v1/shifts/1").status_code == 401
    assert client.patch("/api/v1/shifts/1", json={}).status_code == 401
    assert client.delete("/api/v1/shifts/1").status_code == 401


def test_user_cannot_access_another_users_shift(client: TestClient, auth_headers):
    owner = auth_headers()
    other = auth_headers()
    created = _create(client, owner)
    shift_url = f"/api/v1/shifts/{created['schedule_id']}"

    assert client.get(shift_url, headers=other).status_code == 404
    assert client.patch(shift_url, json={"hourly_wage": 1}, headers=other).status_code == 404
    assert client.delete(shift_url, headers=other).status_code == 404
    assert _list_ids(client, other) == []
    assert client.get(shift_url, headers=owner).json() == created


def test_task_and_shift_apis_only_handle_their_own_kind(client: TestClient, authenticated_user):
    headers = authenticated_user["headers"]
    shift = _create(client, headers)
    task = client.post(
        "/api/v1/tasks",
        json={
            "schedule": {"title": "a", "start_at": _at(15, 10), "end_at": _at(15, 11)},
            "due_date": _at(16, 0),
        },
        headers=headers,
    ).json()
    event = client.post(
        "/api/v1/schedules",
        json={"title": "a", "start_at": _at(15, 10), "end_at": _at(15, 11), "kind": "event"},
        headers=headers,
    ).json()

    # TaskやEventのScheduleにShiftを紐づける経路はない
    for schedule_id in (task["schedule_id"], event["id"]):
        assert client.get(f"/api/v1/shifts/{schedule_id}", headers=headers).status_code == 404
        assert client.patch(
            f"/api/v1/shifts/{schedule_id}", json={"hourly_wage": 1}, headers=headers
        ).status_code == 404
        assert client.delete(f"/api/v1/shifts/{schedule_id}", headers=headers).status_code == 404
    assert client.get(f"/api/v1/tasks/{shift['schedule_id']}", headers=headers).status_code == 404
    assert _list_ids(client, headers) == [shift["schedule_id"]]

    schedule = client.get(f"/api/v1/schedules/{shift['schedule_id']}", headers=headers).json()
    assert schedule["task"] is None and schedule["shift"] is not None
    schedule = client.get(f"/api/v1/schedules/{task['schedule_id']}", headers=headers).json()
    assert schedule["task"] is not None and schedule["shift"] is None


def test_create_shift_rolls_back_schedule_when_shift_insert_fails(
        client: TestClient, authenticated_user, migrated_engine
):
    headers = authenticated_user["headers"]
    # Shiftの保存だけが失敗するよう、shiftsテーブルに常に失敗する制約を付ける
    with migrated_engine.begin() as connection:
        connection.execute(text(
            "ALTER TABLE shifts ADD CONSTRAINT ck_shifts_test_always_fail CHECK (false) NOT VALID"
        ))

    with pytest.raises(Exception):
        client.post("/api/v1/shifts", json=_payload(), headers=headers)

    with migrated_engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM schedules")) == 0
        assert connection.scalar(text("SELECT count(*) FROM shifts")) == 0


def test_delete_shift_handles_planned_transactions(
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
                    "VALUES (:user_id, :schedule_id, :account_id, 'income', 9100, '2026-09-25') "
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
                "VALUES (:user_id, :account_id, :planned_id, 'income', 9100, 'schedule', now())"
            ),
            {"user_id": user_id, "account_id": account_id, "planned_id": actualized_id},
        )

    response = client.delete(f"/api/v1/shifts/{target['schedule_id']}", headers=headers)
    assert response.status_code == 204

    with migrated_engine.connect() as connection:
        planned = dict(connection.execute(
            text("SELECT id, schedule_id FROM planned_transactions")
        ).all())
        assert unactualized_id not in planned
        assert planned == {actualized_id: None}
        assert connection.scalar(text("SELECT count(*) FROM shifts")) == 0
        assert connection.scalar(text("SELECT count(*) FROM schedules")) == 0
