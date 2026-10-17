import jwt, secrets, string
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError, PyJWKClientError
from sqlalchemy.orm import Session
from functools import lru_cache
from typing import Annotated, Any

from app.db import get_db
from app.core.config import settings
from app.core.errors import UnauthorizedError
from app.models.auth import User
from app.repositories import user_repository


# Authorizationヘッダーが無い場合も自前で401を返すため auto_error=False にする
bearer_scheme = HTTPBearer(auto_error=False)

credentials_exception = UnauthorizedError("Could not validate credentials")


# Auth0の公開鍵(JWKS)を取得するクライアント（鍵はクライアント内でキャッシュされる）
@lru_cache
def get_jwks_client() -> jwt.PyJWKClient:
    return jwt.PyJWKClient(settings.auth0_jwks_url)


# トークンのヘッダー(kid)に対応する署名検証用の公開鍵を取得する関数
def get_signing_key(token: str) -> Any:
    return get_jwks_client().get_signing_key_from_jwt(token).key


# Auth0が発行したアクセストークンを検証し、中身(クレーム)を返す関数
def verify_access_token(token: str) -> dict[str, Any]:
    try:
        signing_key = get_signing_key(token)
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=settings.auth0_algorithms,
            audience=settings.auth0_audience,
            issuer=settings.auth0_issuer,
            options={"require": ["exp", "iss", "aud", "sub"]}
        )
    except (InvalidTokenError, PyJWKClientError):
        raise credentials_exception
    return payload


def create_random_username() -> str:
    alphabet_num = string.ascii_lowercase + string.digits
    random_name = "".join(secrets.choice(alphabet_num) for _ in range(20))
    return random_name


def get_user_by_subject(
        auth_subject: str,
        db: Session
) -> User | None:

    return user_repository.get_by_subject(db, auth_subject)


# 初回アクセス時にAuth0のsubをもとにTaskal側のUserを作成する関数
def get_or_create_user(
        auth_subject: str,
        email: str | None,
        db: Session
) -> User:

    user = get_user_by_subject(auth_subject, db)
    if user is not None:
        # メールアドレスはAuth0側で変更されるため、トークンの値と異なれば同期する
        if email is not None and user.email != email:
            return user_repository.update_email(db, user, email)
        return user

    return user_repository.create(
        db,
        User(
            username=create_random_username(),
            email=email,
            auth_subject=auth_subject
        )
    )


async def get_current_user(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
        db: Annotated[Session, Depends(get_db)]
) -> User:

    if credentials is None:
        raise credentials_exception

    payload = verify_access_token(credentials.credentials)
    email = payload.get(settings.auth0_email_claim)
    return get_or_create_user(
        payload["sub"],
        email if isinstance(email, str) else None,
        db
    )
