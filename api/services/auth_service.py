import jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Annotated

from ..db import get_db
from ..core.config import Settings
from ..models.auth import User
from ..schemas.auth import UserReadById, UserAuthenticate, TokenData, UserRegistResponse


password_hash = PasswordHash.recommended()

DUMMY_HASH = password_hash.hash("dummypassword")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")

settings = Settings()


# 実際のパスワードとDBに登録しているハッシュ化されたパスワードが対応しているかチェックする関数
def verify_password(
        plain_password: str,
        hashed_password: str
) -> bool:
    
    return password_hash.verify(
        plain_password,
        hashed_password
    )


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


def get_defalt_username_by_email(email: str) -> str:
    return email.split("@")[0]


def regist_user(
        email: str,
        password: str,
        db: Session
) -> UserRegistResponse:
    
    existing_user = db.scalar(
        select(User)
        .where(
            User.email == email
        )
    )
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The email has already been used."
        )
    
    hashed_password = get_password_hash(password)
    username = get_defalt_username_by_email(email)
    new_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def get_user_by_id(
        user_id: int,
        db: Session
) -> UserReadById | None:
    
    user = db.scalar(
        select(User)
        .where(User.id == user_id)
    )
    if user is None:
        return None
    return user


def authenticate_user(
        user_id: int,
        password: str,
        db: Session
) -> UserAuthenticate | None:
    
    user = get_user_by_id(
        user_id,
        db
    )
    if user is None:
        verify_password(
            password,
            DUMMY_HASH
        )
        return None
    if not verify_password(
        password,
        user.hashed_password
    ):
        return None
    return user


def create_access_token(
        data: dict,
        expires_delta: timedelta | None = None
) -> str:
    
    to_encode = data.copy()

    # 有効期限が指定されている場合 
    if expires_delta is not None:
        expire = datetime.now(timezone.utc) + expires_delta
    
    # 有効期限が指定されていない場合（デフォルトを15分に設定）
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )
    return encoded_jwt


async def get_current_user(
        token: Annotated[str, Depends(oauth2_scheme)],
        db: Annotated[Session, Depends(get_db)]
) -> UserReadById | None:
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-authenticate": "Bearer"}
    )
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)

    except InvalidTokenError:
        raise credentials_exception
    
    user = get_user_by_id(
        token_data.email,
        db
    )
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
        current_user: Annotated[UserAuthenticate, Depends(get_current_user)]
) -> UserAuthenticate:
    
    if current_user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user."
        )
    return current_user