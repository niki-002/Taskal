from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Depends, Query
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationInfo,
    computed_field,
    field_validator,
)
from pydantic_core import PydanticCustomError

from app.core.errors import ValidationError
from app.schemas.schedule import ScheduleBaseCreate, ScheduleBaseResponse, ScheduleUpdate
from app.schemas.types import UTCDatetime

# DBのINTEGER列に保存できる最大値
MAX_DB_INTEGER = 2_147_483_647

HourlyWage = Annotated[int, Field(ge=0, le=MAX_DB_INTEGER, examples=[1300])]
BreakMinutes = Annotated[int, Field(ge=0, le=MAX_DB_INTEGER, examples=[60])]
ShiftWorkplace = Annotated[str, StringConstraints(max_length=200)]


# 勤務時間は分単位で扱い、1分未満（秒以下）は切り捨てる
class WorkingTime:
    @staticmethod
    def minutes(start_at: datetime, end_at: datetime) -> int:
        return (end_at - start_at) // timedelta(minutes=1)


class BreakExceedsWorkingTimeError:
    field = "break_minutes"
    reason = "exceeds_working_time"
    message = "break_minutes must not exceed working time"

    @classmethod
    def to_pydantic(cls) -> PydanticCustomError:
        return PydanticCustomError(cls.reason, cls.message)

    @staticmethod
    def is_exceeded(start_at: datetime, end_at: datetime, break_minutes: int) -> bool:
        return break_minutes > WorkingTime.minutes(start_at, end_at)

    # field はエラーを示すフィールド名。休憩時間を受け取らない予定の更新では "end_at" を指定する
    @classmethod
    def check(
            cls,
            start_at: datetime,
            end_at: datetime,
            break_minutes: int,
            field: str = field,
    ) -> None:
        if cls.is_exceeded(start_at, end_at, break_minutes):
            raise ValidationError(details=[{"field": field, "reason": cls.reason}])


# リクエストスキーマ
# kindはサーバー側で shift に設定するため受け付けない
class ShiftCreate(BaseModel):
    # break_minutes の検証で参照するため、schedule を先に定義する
    schedule: ScheduleBaseCreate
    hourly_wage: HourlyWage
    break_minutes: BreakMinutes = 0
    workplace: ShiftWorkplace | None = Field(None, examples=["新宿店"])

    @field_validator("break_minutes")
    @classmethod
    def _break_within_working_time(cls, break_minutes: int, info: ValidationInfo) -> int:
        schedule = info.data.get("schedule")
        if schedule is not None and BreakExceedsWorkingTimeError.is_exceeded(
            schedule.start_at, schedule.end_at, break_minutes
        ):
            raise BreakExceedsWorkingTimeError.to_pydantic()
        return break_minutes


# 指定したフィールドだけを更新する。Scheduleの項目は schedule の中で指定する
class ShiftUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hourly_wage: HourlyWage | None = None
    break_minutes: BreakMinutes | None = None
    workplace: ShiftWorkplace | None = None
    schedule: ScheduleUpdate | None = None

    # null で消せるのは任意項目（workplace）だけ
    @field_validator("hourly_wage", "break_minutes", "schedule", mode="before")
    @classmethod
    def _reject_null(cls, value):
        if value is None:
            raise PydanticCustomError("not_nullable", "this field cannot be null")
        return value


# 一覧取得の絞り込み条件。期間は [from, to) で、期間と一部でも重なるシフトを対象にする
class ShiftListParams(BaseModel):
    from_at: datetime
    to_at: datetime

    # クエリの from・to から組み立てる（FastAPIの依存関数として使う）
    @classmethod
    def from_query(
            cls,
            from_at: Annotated[UTCDatetime, Query(alias="from")],
            to_at: Annotated[UTCDatetime, Query(alias="to")],
    ) -> "ShiftListParams":
        if to_at <= from_at:
            raise ValidationError(details=[{"field": "to", "reason": "must_be_after_from"}])
        return cls(from_at=from_at, to_at=to_at)


ShiftListParamsDep = Annotated[ShiftListParams, Depends(ShiftListParams.from_query)]


# レスポンススキーマ
class ShiftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    schedule_id: int
    hourly_wage: int
    break_minutes: int
    workplace: str | None
    schedule: ScheduleBaseResponse

    # 見込収入（円）= (勤務時間（分）- break_minutes) × hourly_wage ÷ 60。小数点以下は切り捨てる
    # 浮動小数点の誤差が出ないよう、整数のまま掛けてから割る
    @computed_field
    @property
    def estimated_income(self) -> int:
        working_minutes = WorkingTime.minutes(self.schedule.start_at, self.schedule.end_at)
        return (working_minutes - self.break_minutes) * self.hourly_wage // 60
