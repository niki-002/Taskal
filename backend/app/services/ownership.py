# 他ユーザー所有リソースを404として扱う共通処理
from typing import TypeVar

from app.core.errors import NotFoundError

T = TypeVar("T")


# 存在しない場合も他ユーザー所有の場合も、存在を知らせないため同じ404にする
def require_owned(resource: T | None, message: str = "リソースが見つかりません。") -> T:
    if resource is None:
        raise NotFoundError(message)
    return resource
