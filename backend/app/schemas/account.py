from datetime import datetime
from typing import Annotated, Literal

from fastapi import Depends, Query
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator
from pydantic_core import PydanticCustomError

from app.models.account import Account
from app.schemas.types import MAX_DB_INTEGER, MIN_DB_INTEGER

AccountType = Literal["cash", "bank", "e_money", "other"]

# 前後の空白は除いて扱い、空白だけの名前は受け付けない
AccountName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
# 借入などで残高がマイナスの資産も登録できるよう、負の値も受け付ける
InitialBalance = Annotated[
    int,
    Field(ge=MIN_DB_INTEGER, le=MAX_DB_INTEGER, examples=[120000]),
]


# リクエストスキーマ
class AccountCreate(BaseModel):
    name: AccountName = Field(..., examples=["生活用口座"])
    type: AccountType
    initial_balance: InitialBalance = 0


# 指定したフィールドだけを更新する
# initial_balance は過去のすべての残高に影響するため変更できない（訂正はTransactionで行う）
class AccountUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: AccountName | None = Field(None, examples=["メイン口座"])
    type: AccountType | None = None
    is_active: bool | None = None

    # 任意項目がないため、どのフィールドも null では消せない
    @field_validator("name", "type", "is_active", mode="before")
    @classmethod
    def _reject_null(cls, value):
        if value is None:
            raise PydanticCustomError("not_nullable", "this field cannot be null")
        return value


# 一覧取得の絞り込み条件。is_active を省略した場合は無効化した資産も含めて返す
class AccountListParams(BaseModel):
    is_active: bool | None = None

    # クエリの is_active から組み立てる（FastAPIの依存関数として使う）
    @classmethod
    def from_query(
            cls,
            is_active: Annotated[bool | None, Query()] = None,
    ) -> "AccountListParams":
        return cls(is_active=is_active)


AccountListParamsDep = Annotated[AccountListParams, Depends(AccountListParams.from_query)]


# レスポンススキーマ
class AccountResponse(BaseModel):
    id: int
    name: str
    type: AccountType
    initial_balance: int
    # DBには保存せず、取得のたびにTransactionから計算する
    current_balance: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_account(cls, account: Account, current_balance: int) -> "AccountResponse":
        return cls(
            id=account.id,
            name=account.name,
            type=account.type,
            initial_balance=account.initial_balance,
            current_balance=current_balance,
            is_active=account.is_active,
            created_at=account.created_at,
            updated_at=account.updated_at,
        )
