# データベース取得&セッション作成
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from .core.config import settings

# 環境変数からデータベースのURLを取得
DATABASE_URL = settings.database_url
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set.")

# データベース接続の窓口（アプリはasyncpgで接続する）
db_engine = create_async_engine(
    settings.async_database_url,
    pool_pre_ping=True
)

# 1リクエスト中のDB操作単位
# commit後に属性へアクセスしても暗黙の再読み込み（同期I/O）が起きないよう expire_on_commit=False にする
db_session = async_sessionmaker(
    db_engine,
    autoflush=False,
    expire_on_commit=False
)


# FastAPI依存注入の関数
async def get_db() -> AsyncIterator[AsyncSession]:
    async with db_session() as db:
        yield db
