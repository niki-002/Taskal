from pydantic import BaseModel, Field

# ベーススキーマ
class TaskBase(BaseModel):
    title: str | None = Field(None, example="書類チェック")

# リクエストスキーマ
class TaskCreate(TaskBase):
    pass

# レスポンススキーマ
class TaskCreateResponse(TaskBase):
    id: int

    class Config:
        orm_mode = True