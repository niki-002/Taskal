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


class Page(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = None


# IDなどの整数キーを不透明な文字列カーソルにする
def encode_cursor(last_id: int) -> str:
    return base64.urlsafe_b64encode(str(last_id).encode()).decode()


def decode_cursor(cursor: str | None) -> int | None:
    if cursor is None:
        return None
    try:
        value = int(base64.urlsafe_b64decode(cursor.encode()).decode())
    except (ValueError, binascii.Error, UnicodeDecodeError):
        raise ValidationError(details=[{"field": "cursor", "reason": "invalid_cursor"}])
    if value < 1:
        raise ValidationError(details=[{"field": "cursor", "reason": "invalid_cursor"}])
    return value


class PageParams(BaseModel):
    limit: int = DEFAULT_LIMIT
    after_id: int | None = None


def get_page_params(
        limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
        cursor: Annotated[str | None, Query()] = None,
) -> PageParams:
    return PageParams(limit=limit, after_id=decode_cursor(cursor))


PageParamsDep = Annotated[PageParams, Depends(get_page_params)]


# リポジトリが limit+1 件(id昇順)取得した結果からPageを組み立てる
def build_page(rows: Sequence[T], limit: int) -> Page[T]:
    items = list(rows[:limit])
    next_cursor = encode_cursor(items[-1].id) if len(rows) > limit else None
    return Page(items=items, next_cursor=next_cursor)
