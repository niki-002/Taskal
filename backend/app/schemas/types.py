# 共通のPydantic型
from datetime import datetime, timezone
from typing import Annotated

from pydantic import AfterValidator, AwareDatetime


def _to_utc(value: datetime) -> datetime:
    return value.astimezone(timezone.utc)


# タイムゾーン必須で受け取り、UTCに揃える
UTCDatetime = Annotated[AwareDatetime, AfterValidator(_to_utc)]


# DBのINTEGER列に保存できる範囲。範囲外の値はDBエラー（500）にせず422で返す
MIN_DB_INTEGER = -2_147_483_648
MAX_DB_INTEGER = 2_147_483_647
