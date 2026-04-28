from pydantic import BaseModel, Field, EmailStr


# 新規登録・ログインベーススキーマ
class UserBase(BaseModel):
    username: str = Field(..., min_length=1, examples="World")
    email: EmailStr = Field(...)
    

class UserRegistResponse(UserBase):
    id: int
    hashed_password: str = Field(...)

    
class UserReadById(UserBase):
    id: int
    hashed_password: str = Field(...)
    disabled: bool | None


class UserAuthenticate(UserReadById):
    pass


# Token(=レスポンススキーマ)
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: EmailStr | None = Field(default=None)
