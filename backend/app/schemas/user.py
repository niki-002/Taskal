from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# 前後の空白は除いて扱い、空白だけのユーザー名は受け付けない
Username = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=50),
]


# リクエストスキーマ
class UserUpdate(BaseModel):
    username: Username = Field(..., examples=["new-taskal-user"])


# レスポンススキーマ
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str | None = Field(examples=["user@example.com"])
    username: str = Field(examples=["taskal-user"])
    created_at: datetime
