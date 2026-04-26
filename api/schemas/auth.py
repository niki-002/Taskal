from pydantic import BaseModel, Field, EmailStr


# 新規登録・ログインベーススキーマ
class UserBase(BaseModel):
    username: str = Field(..., min_length=1, examples="World")
    email: EmailStr = Field(...)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserRead(UserBase):
    hashed_password: str = Field(...)
    

# Token(=レスポンススキーマ)
class Token(BaseModel):
    access_token: str
    token_tyoe: str


class TokenData(BaseModel):
    username: str | None = Field(default=None)
