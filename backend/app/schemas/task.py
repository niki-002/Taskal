from datetime import datetime
from typing import Annotated

from fastapi import Depends, Query
from pydantic import BaseModel, ConfigDict, field_validator
from pydantic_core import PydanticCustomError

from app.core.errors import ValidationError
from app.schemas.schedule import ScheduleBaseCreate, ScheduleBaseResponse, ScheduleUpdate
from app.schemas.types import UTCDatetime


# リクエストスキーマ
# kindはサーバー側で task、done_flagは false に設定するため受け付けない
class TaskCreate(BaseModel):
    schedule: ScheduleBaseCreate
    due_date: UTCDatetime


# 指定したフィールドだけを更新する。Scheduleの項目は schedule の中で指定する
class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    done_flag: bool | None = None
    due_date: UTCDatetime | None = None
    schedule: ScheduleUpdate | None = None

    # TaskとScheduleの項目は必須なので null にはできない
    @field_validator("done_flag", "due_date", "schedule", mode="before")
    @classmethod
    def _reject_null(cls, value):
        if value is None:
            raise PydanticCustomError("not_nullable", "this field cannot be null")
        return value


# 一覧取得の絞り込み条件。期限は due_from 以上 due_to 以下を対象にする
class TaskListParams(BaseModel):
    done: bool | None = None
    due_from: datetime | None = None
    due_to: datetime | None = None
    category: str | None = None

    # クエリの done・due_from・due_to・category から組み立てる（FastAPIの依存関数として使う）
    @classmethod
    def from_query(
            cls,
            done: Annotated[bool | None, Query()] = None,
            due_from: Annotated[UTCDatetime | None, Query()] = None,
            due_to: Annotated[UTCDatetime | None, Query()] = None,
            category: Annotated[str | None, Query()] = None,
    ) -> "TaskListParams":
        if due_from is not None and due_to is not None and due_to < due_from:
            raise ValidationError(details=[{"field": "due_to", "reason": "must_not_be_before_due_from"}])
        return cls(done=done, due_from=due_from, due_to=due_to, category=category)


TaskListParamsDep = Annotated[TaskListParams, Depends(TaskListParams.from_query)]


# レスポンススキーマ
class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    schedule_id: int
    due_date: datetime
    done_flag: bool
    schedule: ScheduleBaseResponse
