from pydantic import BaseModel, Field

# ベーススキーマ
class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, example="書類チェック")

# リクエストスキーマ
class TaskCreate(TaskBase):
    pass