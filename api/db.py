# データベース取得&セッション作成
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 環境変数からデータベースのURLを取得
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set.")

# データベース接続の窓口
db_engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

# 1リクエスト中のDB操作単位
db_session = sessionmaker(
    autoflush=False,
    autocommit=False,
    bind=db_engine
)

# FastAPI依存注入の関数
async def get_db():
    db = db_session()
    try:
        yield db
    finally:
        db.close()