import os
import pytest
# FastAPIを実際に起動せずに、HTTPリクエストを擬似的に投げられるクライアント
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# テストデータベースの接続先が設定されてないときに強制停止する安全装置。
TEST_DATABASE_URL = "postgresql+psycopg2://taskal:taskalpass@localhost:5432/taskal_test"
if not TEST_DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL is not set. Create .env from .env.example")

os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from api.database import get_database
from api.models import Base
from api.main import app

# pytest fixture の設計
# テストの前後処理を関数化して使いまわす仕組み

# scope="session"⇒pytest実行中に1回だけ動く
@pytest.fixture(scope="session")
def test_engine():
    test_database_engine = create_engine(TEST_DATABASE_URL,
                                         pool_pre_ping=True)
    # テスト開始時にテーブルを作り直す
    Base.metadata.drop_all(bind=test_database_engine)
    Base.metadata.create_all(bind=test_database_engine)
    yield test_database_engine
    Base.metadata.drop_all(bind=test_database_engine)

# test_engine fixtureのengineを受け取ってそこに紐づくセッションファクトリを作る⇒テスト中にセッションが切れる
@pytest.fixture()
def test_session(test_engine):
    test_database_session = sessionmaker(autoflush=False,
                                         autocommit=False,
                                         bind=test_engine)
    
    def test_get_database():
        database = test_database_session()
        try:
            yield database
        finally:
            database.close()

    # FastAPIのDepends(get_db)を全部置き換える
    app.dependency_overrides[get_database] = test_get_database
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

def test_crud(test_session: TestClient):
    # Create
    response = test_session.post("/api/tasks", json={"title": "test"})
    assert response.status_code == 201
    task = response.json()
    task_id = task["id"]
    assert task["title"] == "test"
    assert task["done_flag"] is False
    
    # Read(一覧)
    response = test_session.get("api/tasks")
    assert response.status_code == 200
    tasks = response.json()
    assert any(task["id"] == task_id for task in tasks)

    # Read(個別)
    response = test_session.get(f"api/tasks/{task_id}")
    assert response.status_code == 200
    task = response.json()
    assert task["title"] == "test"

    # delete
    response = test_session.delete(f"/api/tasks/{task_id}")
    assert response.status_code == 204