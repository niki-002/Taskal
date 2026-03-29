import os
import pytest
# FastAPIを実際に起動せずに、HTTPリクエストを擬似的に投げられるクライアント
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.database import Base, get_database
from api.main import app

TEST_DATABASE_URL = "postgresql+psycopg2://taskal:taskalpass@localhost:5432/taskal_test"