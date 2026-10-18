# カーソル方式ページングのユーティリティ
import base64
import binascii
from typing import Annotated, Generic, Sequence, TypeVar

from fastapi import Depends, Query
from pydantic import BaseModel

from app.core.errors import ValidationError

DEFAULT_LIMIT = 50
MAX_LIMIT = 100

T = TypeVar("T")


# IDなどの整数キーを不透明な文字列カーソルにする
class Cursor:
    @staticmethod
    def encode(last_id: int) -> str:
        return base64.urlsafe_b64encode(str(last_id).encode()).decode()

    @staticmethod
    def decode(cursor: str | None) -> int | None:
        if cursor is None:
            return None
        try:
            value = int(base64.urlsafe_b64decode(cursor.encode()).decode())
        except (ValueError, binascii.Error, UnicodeDecodeError):
            raise ValidationError(details=[{"field": "cursor", "reason": "invalid_cursor"}])
        if value < 1:
            raise ValidationError(details=[{"field": "cursor", "reason": "invalid_cursor"}])
        return value


class Page(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = None

    # リポジトリが limit+1 件(id昇順)取得した結果からPageを組み立てる
    @classmethod
    def from_rows(cls, rows: Sequence[T], limit: int) -> "Page[T]":
        items = list(rows[:limit])
        next_cursor = Cursor.encode(items[-1].id) if len(rows) > limit else None
        return cls(items=items, next_cursor=next_cursor)


class PageParams(BaseModel):
    limit: int = DEFAULT_LIMIT
    after_id: int | None = None

    # クエリの limit・cursor から組み立てる（FastAPIの依存関数として使う）
    @classmethod
    def from_query(
            cls,
            limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
            cursor: Annotated[str | None, Query()] = None,
    ) -> "PageParams":
        return cls(limit=limit, after_id=Cursor.decode(cursor))


PageParamsDep = Annotated[PageParams, Depends(PageParams.from_query)]
