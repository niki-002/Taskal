from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from sqlalchemy.engine import make_url


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    database_url: str
    test_database_url: str | None = None

    # Auth0
    auth0_domain: str     # 例: your-tenant.jp.auth0.com
    auth0_audience: str   # Auth0のAPIに設定したIdentifier
    auth0_algorithms: list[str] = ["RS256"]
    auth0_email_claim: str = "https://taskal.app/email"  # Auth0 Actionでアクセストークンに追加するメールアドレスのクレーム名

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8"
    )

    # Alembicは同期ドライバ(psycopg2)のまま使うため、アプリ用にはドライバをasyncpgに差し替えたURLを使う
    # 例: postgresql+psycopg2://... → postgresql+asyncpg://...
    @property
    def async_database_url(self) -> str:
        return self.to_async_url(self.database_url)

    @staticmethod
    def to_async_url(url: str) -> str:
        return make_url(url).set(drivername="postgresql+asyncpg").render_as_string(hide_password=False)

    @property
    def auth0_issuer(self) -> str:
        return f"https://{self.auth0_domain}/"

    @property
    def auth0_jwks_url(self) -> str:
        return f"https://{self.auth0_domain}/.well-known/jwks.json"

@lru_cache
def get_settings():
    return Settings()

settings = get_settings()
