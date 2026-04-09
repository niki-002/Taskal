from pydantic import BaseModel, Field

# ベーススキーマ
class TaskBase(BaseModel):
    title: str | None = Field(None, example="書類チェック")

# リクエストスキーマ
class TaskCreate(TaskBase):
    pass

    class Config:
        orm_mode = True