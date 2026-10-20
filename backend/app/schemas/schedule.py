from datetime import datetime
from typing import Annotated, Literal

from fastapi import Depends, Query
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationInfo,
    field_validator,
)
from pydantic_core import PydanticCustomError

from app.core.errors import ValidationError
from app.schemas.types import UTCDatetime

ScheduleKind = Literal["event", "task", "shift", "payment"]
# POST /schedules で作成できる種別（task・shiftはそれぞれのAPIで作成する）
CreatableScheduleKind = Literal["event", "payment"]
GoogleSyncStatus = Literal["not_connected", "pending", "synced", "failed"]

# 前後の空白は除いて扱い、空白だけのタイトルは受け付けない
ScheduleTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]
ScheduleDescription = Annotated[str, StringConstraints(max_length=2000)]
ScheduleCategory = Annotated[str, StringConstraints(max_length=50)]


class EndAfterStartError:
    field = "end_at"
    reason = "must_be_after_start_at"
    message = "end_at must be after start_at"

    @classmethod
    def to_pydantic(cls) -> PydanticCustomError:
        return PydanticCustomError(cls.reason, cls.message)

    @classmethod
    def to_detail(cls) -> dict[str, str]:
        return {"field": cls.field, "reason": cls.reason}


# リクエストスキーマ
class ScheduleCreate(BaseModel):
    title: ScheduleTitle = Field(..., examples=["ゼミ"])
    description: ScheduleDescription | None = Field(None, examples=["進捗発表"])
    start_at: UTCDatetime
    end_at: UTCDatetime
    kind: CreatableScheduleKind
    category: ScheduleCategory | None = Field(None, examples=["class"])

    @field_validator("end_at")
    @classmethod
    def _end_after_start(cls, end_at: datetime, info: ValidationInfo) -> datetime:
        start_at = info.data.get("start_at")
        if start_at is not None and end_at <= start_at:
            raise EndAfterStartError.to_pydantic()
        return end_at


# 指定したフィールドだけを更新する。kindは作成後に変更できないため受け付けない
class ScheduleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: ScheduleTitle | None = Field(None, examples=["ゼミ（教室変更）"])
    description: ScheduleDescription | None = None
    start_at: UTCDatetime | None = None
    end_at: UTCDatetime | None = None
    category: ScheduleCategory | None = None

    # null で消せるのは任意項目（description・category）だけ
    @field_validator("title", "start_at", "end_at", mode="before")
    @classmethod
    def _reject_null(cls, value):
        if value is None:
            raise PydanticCustomError("not_nullable", "this field cannot be null")
        return value


# 一覧取得の絞り込み条件。期間は [from, to) で、期間と一部でも重なる予定を対象にする
class ScheduleListParams(BaseModel):
    from_at: datetime
    to_at: datetime
    kinds: list[ScheduleKind] = []
    category: str | None = None

    # クエリの from・to・kind・category から組み立てる（FastAPIの依存関数として使う）
    @classmethod
    def from_query(
            cls,
            from_at: Annotated[UTCDatetime, Query(alias="from")],
            to_at: Annotated[UTCDatetime, Query(alias="to")],
            kind: Annotated[list[ScheduleKind] | None, Query()] = None,
            category: Annotated[str | None, Query()] = None,
    ) -> "ScheduleListParams":
        if to_at <= from_at:
            raise ValidationError(details=[{"field": "to", "reason": "must_be_after_from"}])
        return cls(from_at=from_at, to_at=to_at, kinds=kind or [], category=category)


ScheduleListParamsDep = Annotated[ScheduleListParams, Depends(ScheduleListParams.from_query)]


# レスポンススキーマ
class ScheduleTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    due_date: datetime
    done_flag: bool


class ScheduleShiftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hourly_wage: int
    break_minutes: int
    workplace: str | None


class ScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    start_at: datetime
    end_at: datetime
    kind: ScheduleKind
    category: str | None
    task: ScheduleTaskResponse | None = None
    shift: ScheduleShiftResponse | None = None
    # Google Calendar連携は未実装のため、当面は not_connected 固定
    google_sync_status: GoogleSyncStatus = "not_connected"
    created_at: datetime
    updated_at: datetime
