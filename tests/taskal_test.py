import os
import pytest
# FastAPIを実際に起動せずに、HTTPリクエストを擬似的に投げられるクライアント
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.database import Base, get_database
from api.main import app

# テストデータベースの接続先が設定されてないときに強制停止する安全装置。
TEST_DATABASE_URL = "postgresql+psycopg2://taskal:taskalpass@localhost:5432/taskal_test"
if not TEST_DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL is not set. Create .env from .env.example")

# pytest fixture の設計
# テストの前後処理を関数化して使いまわす仕組み
