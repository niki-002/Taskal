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

class TaskReadResponse(TaskBase):
    id: int
    done_flag: bool = Field(False, description="完了フラグ")

    class Config:
        orm_mode = True