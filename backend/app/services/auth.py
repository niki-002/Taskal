import jwt, secrets, string
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError, PyJWKClientError
from functools import cached_property
from typing import Annotated, Any

from app.core.config import settings
from app.core.errors import UnauthorizedError
from app.models.auth import User
from app.repositories.user import UserRepository, UserRepositoryDep


# Authorizationヘッダーが無い場合も自前で401を返すため auto_error=False にする
bearer_scheme = HTTPBearer(auto_error=False)

credentials_exception = UnauthorizedError("Could not validate credentials")


# Auth0が発行したアクセストークンを検証するクラス
class TokenVerifier:
    # Auth0の公開鍵(JWKS)を取得するクライアント（鍵はクライアント内でキャッシュされる）
    @cached_property
    def jwks_client(self) -> jwt.PyJWKClient:
        return jwt.PyJWKClient(settings.auth0_jwks_url)

    # トークンのヘッダー(kid)に対応する署名検証用の公開鍵を取得する
    def get_signing_key(self, token: str) -> Any:
        return self.jwks_client.get_signing_key_from_jwt(token).key

    # トークンを検証し、中身(クレーム)を返す
    def verify_access_token(self, token: str) -> dict[str, Any]:
        try:
            signing_key = self.get_signing_key(token)
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


# JWKSのキャッシュをリクエスト間で共有するため、1つのインスタンスを使い回す
token_verifier = TokenVerifier()


def get_token_verifier() -> TokenVerifier:
    return token_verifier


# Auth0のユーザーとTaskal側のUserを対応付けるクラス
class AuthService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    @staticmethod
    def create_random_username() -> str:
        alphabet_num = string.ascii_lowercase + string.digits
        random_name = "".join(secrets.choice(alphabet_num) for _ in range(20))
        return random_name

    # 初回アクセス時にAuth0のsubをもとにTaskal側のUserを作成する
    def get_or_create_user(
            self,
            auth_subject: str,
            email: str | None
    ) -> User:

        user = self.repository.get_by_subject(auth_subject)
        if user is not None:
            # メールアドレスはAuth0側で変更されるため、トークンの値と異なれば同期する
            if email is not None and user.email != email:
                return self.repository.update_email(user, email)
            return user

        return self.repository.create(
            User(
                username=self.create_random_username(),
                email=email,
                auth_subject=auth_subject
            )
        )


def get_auth_service(repository: UserRepositoryDep) -> AuthService:
    return AuthService(repository)


TokenVerifierDep = Annotated[TokenVerifier, Depends(get_token_verifier)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


# DBアクセスと公開鍵の取得が同期処理のため、async defにせずスレッドプールで実行させる
def get_current_user(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
        verifier: TokenVerifierDep,
        service: AuthServiceDep
) -> User:

    if credentials is None:
        raise credentials_exception

    payload = verifier.verify_access_token(credentials.credentials)
    email = payload.get(settings.auth0_email_claim)
    return service.get_or_create_user(
        payload["sub"],
        email if isinstance(email, str) else None
    )


CurrentUserDep = Annotated[User, Depends(get_current_user)]
