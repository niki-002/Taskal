import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 環境変数からデータベースのURLを取得
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set.")

# データベース接続の窓口
database_engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# 1リクエスト中のDB操作単位
database_session = sessionmaker(autoflush=False, 
                                autocommit=False, 
                                bind=database_engine)

# FastAPI依存注入の関数
def get_database():
    database = database_session()
    try:
        yield database
    finally:
        database.close()
