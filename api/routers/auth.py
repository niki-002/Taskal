from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm 
from sqlalchemy.orm import Session

from typing import Annotated
from datetime import timedelta

from api.schemas.auth import Token, UserRegistResponse, UserAuthenticate
from api.services import auth_service
from api.db import get_db
from ..core.config import Settings

settings = Settings()

router = APIRouter(prefix="/api/auth")


@router.post(
    "",
    response_model=UserRegistResponse
)
async def regist_user(
    regist_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)]
):
    email = regist_data.username
    password = regist_data.password
    new_user = auth_service.regist_user(
        email,
        password,
        db
    )
    return new_user


@router.post(
    "/token",
    response_model=Token
)
async def get_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)]
):
    email = form_data.username
    password = form_data.password
    user = auth_service.authenticate_user(
        email,
        password,
        db
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = auth_service.create_access_token(
        data={
            "sub": user.email,
            "exp": None
        },
        expires_delta=access_token_expires
    )
    return Token(
        access_token=access_token,
        token_type="bearer"
    )


@router.get("/users/me", response_model=UserAuthenticate)
async def read_users_me(
    current_user: Annotated[UserAuthenticate, Depends(auth_service.get_current_active_user)]
):
    return current_user