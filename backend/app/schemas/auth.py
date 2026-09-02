from pydantic import BaseModel, Field, EmailStr


# 新規登録・ログインベーススキーマ
class UserBase(BaseModel):
    username: str = Field(
        ...,
        min_length=1,
        examples=["World"],
        pattern=r"^[a-zA-Z0-9_-]" # ユーザ名に使える文字の指定
    )
    email: EmailStr = Field(...)
    

class UserRegistResponse(UserBase):
    id: int

    
class UserReadByEmail(UserBase):
    id: int
    hashed_password: str = Field(...)
    disabled: bool | None


class UserAuthenticate(UserReadByEmail):
    pass


# Token(=レスポンススキーマ)
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: EmailStr | None = Field(default=None)
