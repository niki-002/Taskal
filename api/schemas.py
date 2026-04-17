from pydantic import BaseModel, Field
from datetime import date

# ベーススキーマ
class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, example="書類チェック")

class Task(BaseModel):
    id: int
    description: str = Field(max_length=1000, example="赤字を中心に見る。")
    limit: date
    done_flag: bool

# リクエストスキーマ
class TaskCreate(TaskBase):
    description: str = Field(max_length=1000, example="赤字を中心に見る。")
    limit: date

class TaskUpdate(TaskCreate):
    pass

# レスポンススキーマ
class CreatedTask(Task):
    pass    

class ReadTaskList(Task):
    pass

class ReadTask(Task):
    pass

class UpdatedTask(Task):
    pass

class DeletedTask():
    None
    