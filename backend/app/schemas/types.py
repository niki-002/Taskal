# 共通のPydantic型
from datetime import datetime, timezone
from typing import Annotated

from pydantic import AfterValidator, AwareDatetime


def _to_utc(value: datetime) -> datetime:
    return value.astimezone(timezone.utc)


# タイムゾーン必須で受け取り、UTCに揃える
UTCDatetime = Annotated[AwareDatetime, AfterValidator(_to_utc)]
