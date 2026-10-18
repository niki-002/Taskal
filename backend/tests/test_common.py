import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError as PydanticValidationError

from app.core import errors
from app.core.errors import (
    AppError,
    BadRequestError,
    ConflictError,
    ExternalServiceError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from app.core.pagination import (
    PageParamsDep,
    build_page,
    decode_cursor,
    encode_cursor,
)
from app.schemas.types import UTCDatetime
from app.services.ownership import require_owned


# ---- エラー形式 ----

def _error_app() -> TestClient:
    app = FastAPI()
    errors.register_exception_handlers(app)
    router = APIRouter()

    @router.get("/raise/{kind}")
    def raise_error(kind: str):
        raise {
            "400": BadRequestError,
            "401": UnauthorizedError,
            "404": NotFoundError,
            "409": ConflictError,
            "422": ValidationError,
            "502": ExternalServiceError,
        }[kind]()

    class Body(BaseModel):
        name: str

    @router.post("/body")
    def body(payload: Body):
        return payload

    app.include_router(router)
    return TestClient(app)


@pytest.mark.parametrize(
    "status_code, code",
    [
        (400, "BAD_REQUEST"),
        (401, "UNAUTHORIZED"),
        (404, "NOT_FOUND"),
        (409, "CONFLICT"),
        (422, "VALIDATION_ERROR"),
        (502, "EXTERNAL_SERVICE_ERROR"),
    ],
)
def test_app_errors_use_common_format(status_code, code):
    response = _error_app().get(f"/raise/{status_code}")

    assert response.status_code == status_code
    error = response.json()["error"]
    assert error["code"] == code
    assert error["message"]
    assert error["details"] == []


def test_unauthorized_has_www_authenticate_header():
    response = _error_app().get("/raise/401")

    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_request_validation_error_uses_common_format():
    response = _error_app().post("/body", json={})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"] == [{"field": "name", "reason": "missing"}]


def test_unknown_route_uses_common_format():
    response = _error_app().get("/missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_custom_message_and_details():
    error = AppError("msg", [{"field": "x", "reason": "y"}])

    assert error.message == "msg"
    assert error.details == [{"field": "x", "reason": "y"}]


def test_api_returns_common_error_format(client: TestClient, authenticated_user):
    response = client.get("/api/v1/tasks")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"

    response = client.get("/api/v1/tasks/9999", headers=authenticated_user["headers"])
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"

    response = client.post(
        "/api/v1/tasks", json={}, headers=authenticated_user["headers"]
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_old_api_path_is_removed(client: TestClient, authenticated_user):
    response = client.get("/api/tasks", headers=authenticated_user["headers"])

    assert response.status_code == 404


# ---- ページング ----

def test_cursor_round_trip():
    assert decode_cursor(encode_cursor(42)) == 42
    assert decode_cursor(None) is None


@pytest.mark.parametrize("cursor", ["!!!", "YWJj", encode_cursor(0)])
def test_invalid_cursor_raises_validation_error(cursor):
    with pytest.raises(ValidationError):
        decode_cursor(cursor)


class _Row:
    def __init__(self, id: int):
        self.id = id


def test_build_page_with_next_cursor():
    page = build_page([_Row(1), _Row(2), _Row(3)], limit=2)

    assert [row.id for row in page.items] == [1, 2]
    assert decode_cursor(page.next_cursor) == 2


def test_build_page_last_page_has_no_cursor():
    page = build_page([_Row(1), _Row(2)], limit=2)

    assert len(page.items) == 2
    assert page.next_cursor is None


def _page_params_client() -> TestClient:
    app = FastAPI()
    errors.register_exception_handlers(app)

    @app.get("/params")
    def params(page: PageParamsDep):
        return page

    return TestClient(app)


def test_page_params_default_and_values():
    client = _page_params_client()

    assert client.get("/params").json() == {"limit": 50, "after_id": None}
    response = client.get("/params", params={"limit": 100, "cursor": encode_cursor(7)})
    assert response.json() == {"limit": 100, "after_id": 7}


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"cursor": "!!!"}])
def test_page_params_invalid(params):
    response = _page_params_client().get("/params", params=params)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_task_repository_pagination(client: TestClient, authenticated_user):
    from app.db import get_db
    from app.main import app
    from app.models.auth import User
    from app.repositories import task_repository
    from app.services import task_service
    from sqlalchemy import select

    for i in range(3):
        client.post(
            "/api/v1/tasks",
            json={"title": f"t{i}", "description": "d", "limit": "2026-05-01"},
            headers=authenticated_user["headers"],
        )
    db = next(app.dependency_overrides[get_db]())
    try:
        owner_id = db.scalar(select(User.id))
        rows = task_repository.list_page_by_owner(db, owner_id, limit=2)
        # Taskの主キーはschedule_idのため、idを持つレスポンスに変換してからページにする
        page = build_page([task_service.to_response(row) for row in rows], 2)
        assert len(page.items) == 2 and page.next_cursor
        rows = task_repository.list_page_by_owner(
            db, owner_id, limit=2, after_id=decode_cursor(page.next_cursor)
        )
        page2 = build_page([task_service.to_response(row) for row in rows], 2)
        assert len(page2.items) == 1 and page2.next_cursor is None
    finally:
        db.close()


# ---- 日時型 ----

class _Model(BaseModel):
    at: UTCDatetime


def test_utc_datetime_converts_to_utc():
    value = _Model(at="2026-09-10T09:00:00+09:00").at

    assert value.isoformat() == "2026-09-10T00:00:00+00:00"


def test_utc_datetime_accepts_z():
    assert _Model(at="2026-09-10T00:00:00Z").at.utcoffset().total_seconds() == 0


def test_utc_datetime_rejects_naive():
    with pytest.raises(PydanticValidationError):
        _Model(at="2026-09-10T09:00:00")


# ---- 所有者チェック ----

def test_require_owned():
    assert require_owned("x") == "x"
    with pytest.raises(NotFoundError):
        require_owned(None)
