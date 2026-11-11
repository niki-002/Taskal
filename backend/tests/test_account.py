from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import text

from app.core.errors import NotFoundError
from app.core.pagination import Cursor, PageParams
from app.models.account import Account
from app.models.auth import User
from app.schemas.account import AccountCreate, AccountListParams, AccountUpdate
from app.services.account import AccountService

BASE_AT = datetime(2026, 9, 15, 1, 0, tzinfo=timezone.utc)


# ---- AccountService（DB不要） ----

class FakeAccountRepository:
    def __init__(
            self,
            accounts: list[Account] | None = None,
            totals: dict[int, tuple[int, int]] | None = None,
    ):
        self.accounts = accounts or []
        self.totals = totals or {}
        self.saved: list[Account] = []
        self.list_calls: list[dict] = []
        self.sum_calls: list[list[int]] = []

    async def get_by_id(self, account_id: int, owner_id: int) -> Account | None:
        return next(
            (a for a in self.accounts if a.id == account_id and a.user_id == owner_id),
            None,
        )

    async def list_page(self, owner_id, limit, is_active=None, after_id=None):
        self.list_calls.append({
            "owner_id": owner_id,
            "limit": limit,
            "is_active": is_active,
            "after_id": after_id,
        })
        return [a for a in self.accounts if a.user_id == owner_id][:limit + 1]

    async def sum_transactions(self, account_ids):
        self.sum_calls.append(list(account_ids))
        return {i: self.totals[i] for i in account_ids if i in self.totals}

    async def add(self, account: Account) -> Account:
        account.id = len(self.accounts) + 1
        account.created_at = account.updated_at = BASE_AT
        self.accounts.append(account)
        return account

    async def save(self, account: Account) -> Account:
        self.saved.append(account)
        return account


def _make_user(user_id: int = 1) -> User:
    return User(id=user_id, username=f"user{user_id}", auth_subject=f"auth0|user{user_id}")


def _make_account(
        account_id: int,
        user_id: int = 1,
        initial_balance: int = 10000,
        is_active: bool = True,
) -> Account:
    return Account(
        id=account_id,
        user_id=user_id,
        name=f"account{account_id}",
        type="bank",
        initial_balance=initial_balance,
        is_active=is_active,
        created_at=BASE_AT,
        updated_at=BASE_AT,
    )


def _make_service(accounts=None, totals=None):
    repository = FakeAccountRepository(accounts, totals)
    return AccountService(repository), repository


@pytest.mark.anyio
async def test_service_create_account_sets_owner_and_active():
    service, repository = _make_service()

    response = await service.create_account(
        AccountCreate(name=" 生活用口座 ", type="bank", initial_balance=120000),
        _make_user(7),
    )

    created = repository.accounts[0]
    assert created.user_id == 7
    assert created.is_active is True
    assert response.name == "生活用口座"
    assert response.initial_balance == 120000
    assert response.current_balance == 120000


def test_account_create_initial_balance_defaults_to_zero():
    assert AccountCreate(name="財布", type="cash").initial_balance == 0


@pytest.mark.anyio
async def test_service_get_account_calculates_current_balance():
    service, repository = _make_service(
        [_make_account(1, initial_balance=10000)],
        totals={1: (5000, 3000)},
    )

    response = await service.get_account(1, _make_user())

    # 10000 + 5000 - 3000
    assert response.current_balance == 12000
    assert response.initial_balance == 10000
    assert repository.sum_calls == [[1]]


@pytest.mark.anyio
async def test_service_current_balance_can_be_negative():
    service, _ = _make_service(
        [_make_account(1, initial_balance=1000)],
        totals={1: (0, 3000)},
    )

    assert (await service.get_account(1, _make_user())).current_balance == -2000


@pytest.mark.anyio
async def test_service_get_other_users_account_raises_not_found():
    service, _ = _make_service([_make_account(1, user_id=2)])

    with pytest.raises(NotFoundError):
        await service.get_account(1, _make_user(1))


@pytest.mark.anyio
async def test_service_list_accounts_sums_transactions_at_once_and_builds_next_cursor():
    accounts = [_make_account(i) for i in range(1, 4)]
    service, repository = _make_service(accounts, totals={1: (100, 0), 2: (0, 100)})

    page = await service.list_accounts(
        AccountListParams(is_active=True),
        PageParams(limit=2, after_id=None),
        _make_user(),
    )

    assert [item.id for item in page.items] == [1, 2]
    assert [item.current_balance for item in page.items] == [10100, 9900]
    assert page.next_cursor == Cursor.encode(2)
    assert repository.list_calls == [
        {"owner_id": 1, "limit": 2, "is_active": True, "after_id": None}
    ]
    # limit+1 件目も含めて1回のクエリで合計を取得する
    assert repository.sum_calls == [[1, 2, 3]]


@pytest.mark.anyio
async def test_service_list_accounts_passes_cursor_and_filter():
    service, repository = _make_service()

    page = await service.list_accounts(
        AccountListParams(),
        PageParams(limit=10, after_id=5),
        _make_user(),
    )

    assert page.items == []
    assert repository.list_calls[0]["is_active"] is None
    assert repository.list_calls[0]["after_id"] == 5


@pytest.mark.anyio
async def test_service_update_account_changes_only_specified_fields():
    target = _make_account(1)
    service, repository = _make_service([target], totals={1: (500, 0)})

    response = await service.update_account(
        1, AccountUpdate(name="メイン口座", is_active=False), _make_user()
    )

    assert response.name == "メイン口座"
    assert response.type == "bank"
    assert response.is_active is False
    assert response.initial_balance == 10000
    assert response.current_balance == 10500
    assert repository.saved == [target]


def test_account_update_rejects_initial_balance():
    with pytest.raises(PydanticValidationError) as exc_info:
        AccountUpdate(initial_balance=0)

    error = exc_info.value.errors()[0]
    assert error["loc"] == ("initial_balance",)
    assert error["type"] == "extra_forbidden"


@pytest.mark.anyio
async def test_service_delete_account_deactivates_instead_of_deleting():
    target = _make_account(1)
    service, repository = _make_service([target])

    await service.delete_account(1, _make_user())

    assert target.is_active is False
    assert repository.saved == [target]
    assert repository.accounts == [target]


@pytest.mark.anyio
async def test_service_delete_other_users_account_does_nothing():
    target = _make_account(1, user_id=2)
    service, repository = _make_service([target])

    with pytest.raises(NotFoundError):
        await service.delete_account(1, _make_user(1))
    assert target.is_active is True
    assert repository.saved == []


# ---- Accounts API（DB使用） ----

def _payload(**overrides) -> dict:
    return {"name": "生活用口座", "type": "bank", "initial_balance": 120000, **overrides}


def _create(client: TestClient, headers, **overrides) -> dict:
    response = client.post("/api/v1/accounts", json=_payload(**overrides), headers=headers)
    assert response.status_code == 201, response.json()
    return response.json()


def _list_ids(client: TestClient, headers, **params) -> list[int]:
    response = client.get("/api/v1/accounts", params=params, headers=headers)
    assert response.status_code == 200, response.json()
    return [item["id"] for item in response.json()["items"]]


def _add_transaction(engine, account: dict, user_id: int, type_: str, amount: int) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO transactions (user_id, account_id, type, amount, source, occurred_at) "
                "VALUES (:user_id, :account_id, :type, :amount, 'manual', now())"
            ),
            {"user_id": user_id, "account_id": account["id"], "type": type_, "amount": amount},
        )


def _user_id(client: TestClient, headers) -> int:
    return client.get("/api/v1/users/me", headers=headers).json()["id"]


def test_account_crud(client: TestClient, authenticated_user):
    headers = authenticated_user["headers"]

    created = _create(client, headers)
    assert set(created) == {
        "id", "name", "type", "initial_balance", "current_balance", "is_active",
        "created_at", "updated_at",
    }
    assert created["name"] == "生活用口座"
    assert created["type"] == "bank"
    assert created["initial_balance"] == 120000
    assert created["current_balance"] == 120000
    assert created["is_active"] is True

    account_url = f"/api/v1/accounts/{created['id']}"
    response = client.get(account_url, headers=headers)
    assert response.status_code == 200
    assert response.json() == created

    response = client.patch(
        account_url, json={"name": "メイン口座", "type": "e_money"}, headers=headers
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["name"] == "メイン口座"
    assert updated["type"] == "e_money"
    assert updated["initial_balance"] == 120000
    assert updated["is_active"] is True
    assert client.get(account_url, headers=headers).json() == updated

    response = client.delete(account_url, headers=headers)
    assert response.status_code == 204
    # 物理削除しないため、無効化した資産も取得できる
    response = client.get(account_url, headers=headers)
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    # 再度有効にできる
    response = client.patch(account_url, json={"is_active": True}, headers=headers)
    assert response.status_code == 200
    assert response.json()["is_active"] is True


def test_create_account_with_only_required_fields(client: TestClient, authenticated_user):
    response = client.post(
        "/api/v1/accounts",
        json={"name": "財布", "type": "cash"},
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 201
    assert response.json()["initial_balance"] == 0
    assert response.json()["current_balance"] == 0


@pytest.mark.parametrize("type_", ["cash", "bank", "e_money", "other"])
def test_create_account_accepts_each_type(client: TestClient, authenticated_user, type_):
    assert _create(client, authenticated_user["headers"], type=type_)["type"] == type_


@pytest.mark.parametrize("initial_balance", [-2_147_483_648, 0, 2_147_483_647])
def test_create_account_accepts_initial_balance_in_db_range(
        client: TestClient, authenticated_user, initial_balance
):
    created = _create(client, authenticated_user["headers"], initial_balance=initial_balance)

    assert created["initial_balance"] == created["current_balance"] == initial_balance


def test_create_account_strips_name_and_accepts_max_length(client: TestClient, authenticated_user):
    headers = authenticated_user["headers"]

    assert _create(client, headers, name="  財布  ")["name"] == "財布"
    assert _create(client, headers, name="a" * 100)["name"] == "a" * 100


def test_create_account_ignores_server_fields(client: TestClient, authenticated_user):
    created = _create(
        client,
        authenticated_user["headers"],
        current_balance=1,
        is_active=False,
        user_id=999,
    )

    assert created["current_balance"] == 120000
    assert created["is_active"] is True


@pytest.mark.parametrize(
    ("overrides", "field", "reason"),
    [
        ({"name": ""}, "name", "string_too_short"),
        ({"name": "   "}, "name", "string_too_short"),
        ({"name": "a" * 101}, "name", "string_too_long"),
        ({"name": None}, "name", "string_type"),
        ({"type": "credit"}, "type", "literal_error"),
        ({"type": None}, "type", "literal_error"),
        ({"initial_balance": 1.5}, "initial_balance", "int_from_float"),
        ({"initial_balance": None}, "initial_balance", "int_type"),
        # DBのINTEGERに入らない値は500にせず422で返す
        ({"initial_balance": 2_147_483_648}, "initial_balance", "less_than_equal"),
        ({"initial_balance": -2_147_483_649}, "initial_balance", "greater_than_equal"),
    ],
)
def test_create_account_validation(
        client: TestClient, authenticated_user, overrides, field, reason
):
    response = client.post(
        "/api/v1/accounts",
        json=_payload(**overrides),
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"] == [{"field": field, "reason": reason}]


def test_create_account_requires_name_and_type(client: TestClient, authenticated_user):
    response = client.post("/api/v1/accounts", json={}, headers=authenticated_user["headers"])

    assert response.status_code == 422
    assert response.json()["error"]["details"] == [
        {"field": "name", "reason": "missing"},
        {"field": "type", "reason": "missing"},
    ]


@pytest.mark.parametrize(
    ("payload", "field", "reason"),
    [
        ({"name": None}, "name", "not_nullable"),
        ({"type": None}, "type", "not_nullable"),
        ({"is_active": None}, "is_active", "not_nullable"),
        ({"name": " "}, "name", "string_too_short"),
        ({"name": "a" * 101}, "name", "string_too_long"),
        ({"type": "credit"}, "type", "literal_error"),
        ({"is_active": "maybe"}, "is_active", "bool_parsing"),
        # initial_balance は作成後に変更できない
        ({"initial_balance": 0}, "initial_balance", "extra_forbidden"),
        ({"current_balance": 0}, "current_balance", "extra_forbidden"),
    ],
)
def test_update_account_validation(client: TestClient, authenticated_user, payload, field, reason):
    headers = authenticated_user["headers"]
    created = _create(client, headers)
    account_url = f"/api/v1/accounts/{created['id']}"

    response = client.patch(account_url, json=payload, headers=headers)

    assert response.status_code == 422
    assert response.json()["error"]["details"] == [{"field": field, "reason": reason}]
    assert client.get(account_url, headers=headers).json() == created


def test_update_account_with_empty_body_changes_nothing(client: TestClient, authenticated_user):
    headers = authenticated_user["headers"]
    created = _create(client, headers)

    response = client.patch(f"/api/v1/accounts/{created['id']}", json={}, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert {k: v for k, v in body.items() if k != "updated_at"} == {
        k: v for k, v in created.items() if k != "updated_at"
    }


def test_current_balance_reflects_transactions(
        client: TestClient, authenticated_user, migrated_engine
):
    headers = authenticated_user["headers"]
    user_id = _user_id(client, headers)
    account = _create(client, headers, initial_balance=10000)
    other_account = _create(client, headers, initial_balance=500)

    _add_transaction(migrated_engine, account, user_id, "income", 3000)
    _add_transaction(migrated_engine, account, user_id, "income", 2000)
    _add_transaction(migrated_engine, account, user_id, "expense", 1500)
    _add_transaction(migrated_engine, other_account, user_id, "expense", 800)

    # 10000 + (3000 + 2000) - 1500
    response = client.get(f"/api/v1/accounts/{account['id']}", headers=headers)
    assert response.json()["current_balance"] == 13500
    assert response.json()["initial_balance"] == 10000

    items = client.get("/api/v1/accounts", headers=headers).json()["items"]
    assert {item["id"]: item["current_balance"] for item in items} == {
        account["id"]: 13500,
        other_account["id"]: -300,
    }

    # 更新・無効化後のレスポンスも現在残高を計算して返す
    response = client.patch(
        f"/api/v1/accounts/{account['id']}", json={"name": "x"}, headers=headers
    )
    assert response.json()["current_balance"] == 13500

    with migrated_engine.connect() as connection:
        columns = connection.scalars(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'accounts'"
        )).all()
    assert "current_balance" not in columns


def test_current_balance_handles_totals_beyond_db_integer(
        client: TestClient, authenticated_user, migrated_engine
):
    headers = authenticated_user["headers"]
    user_id = _user_id(client, headers)
    account = _create(client, headers, initial_balance=2_147_483_647)

    _add_transaction(migrated_engine, account, user_id, "income", 2_147_483_647)
    _add_transaction(migrated_engine, account, user_id, "income", 2_147_483_647)

    response = client.get(f"/api/v1/accounts/{account['id']}", headers=headers)
    assert response.json()["current_balance"] == 3 * 2_147_483_647


def test_delete_account_keeps_transactions(
        client: TestClient, authenticated_user, migrated_engine
):
    headers = authenticated_user["headers"]
    user_id = _user_id(client, headers)
    account = _create(client, headers, initial_balance=1000)
    _add_transaction(migrated_engine, account, user_id, "income", 500)

    response = client.delete(f"/api/v1/accounts/{account['id']}", headers=headers)
    assert response.status_code == 204
    # 無効化済みの資産を再度削除しても204を返す
    response = client.delete(f"/api/v1/accounts/{account['id']}", headers=headers)
    assert response.status_code == 204

    with migrated_engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM accounts")) == 1
        assert connection.scalar(text("SELECT count(*) FROM transactions")) == 1

    body = client.get(f"/api/v1/accounts/{account['id']}", headers=headers).json()
    assert body["is_active"] is False
    assert body["current_balance"] == 1500


def test_list_accounts_filters_by_is_active(client: TestClient, authenticated_user):
    headers = authenticated_user["headers"]
    active = _create(client, headers)
    inactive = _create(client, headers)
    client.delete(f"/api/v1/accounts/{inactive['id']}", headers=headers)

    assert _list_ids(client, headers) == [active["id"], inactive["id"]]
    assert _list_ids(client, headers, is_active="true") == [active["id"]]
    assert _list_ids(client, headers, is_active="false") == [inactive["id"]]


def test_list_accounts_pagination(client: TestClient, authenticated_user):
    headers = authenticated_user["headers"]
    expected = [_create(client, headers)["id"] for _ in range(3)]

    first = client.get("/api/v1/accounts", params={"limit": 2}, headers=headers).json()
    assert [item["id"] for item in first["items"]] == expected[:2]
    assert first["next_cursor"] is not None

    second = client.get(
        "/api/v1/accounts",
        params={"limit": 2, "cursor": first["next_cursor"]},
        headers=headers,
    ).json()
    assert [item["id"] for item in second["items"]] == expected[2:]
    assert second["next_cursor"] is None


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"is_active": "maybe"}, "is_active"),
        ({"cursor": "invalid"}, "cursor"),
        ({"limit": 0}, "limit"),
        ({"limit": 101}, "limit"),
    ],
)
def test_list_accounts_validation(client: TestClient, authenticated_user, params, field):
    response = client.get(
        "/api/v1/accounts", params=params, headers=authenticated_user["headers"]
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == field


def test_accounts_require_authentication(client: TestClient):
    assert client.get("/api/v1/accounts").status_code == 401
    assert client.post("/api/v1/accounts", json=_payload()).status_code == 401
    assert client.get("/api/v1/accounts/1").status_code == 401
    assert client.patch("/api/v1/accounts/1", json={}).status_code == 401
    assert client.delete("/api/v1/accounts/1").status_code == 401


def test_user_cannot_access_another_users_account(client: TestClient, auth_headers):
    owner = auth_headers()
    other = auth_headers()
    created = _create(client, owner)
    account_url = f"/api/v1/accounts/{created['id']}"

    assert client.get(account_url, headers=other).status_code == 404
    assert client.patch(account_url, json={"name": "x"}, headers=other).status_code == 404
    assert client.delete(account_url, headers=other).status_code == 404
    assert _list_ids(client, other) == []
    assert client.get(account_url, headers=owner).json() == created


def test_get_unknown_account_returns_not_found(client: TestClient, authenticated_user):
    response = client.get("/api/v1/accounts/999999", headers=authenticated_user["headers"])

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
