from pydantic import BaseModel, Field
from datetime import date

# ベーススキーマ
class TaskBase(BaseModel):
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        examples=["書類チェック"]
        )


# リクエストスキーマ
class TaskCreate(TaskBase):
    description: str = Field(max_length=1000, examples=["赤字を中心に見る。"])
    limit: date


class TaskUpdate(TaskCreate):
    title: str
    description: str
    limit: date


# レスポンススキーマ
class TaskResponse(TaskBase):
    id: int
    owner_id: int
    description: str = Field(max_length=1000, examples=["赤字を中心に見る。"])
    limit: date
    done_flag: bool


class TaskDeleteResponse():
    None
    