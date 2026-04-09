import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set.")

database_engine = create_engine(DATABASE_URL, pool_pre_ping=True)

database_session = sessionmaker(autoflush=False, 
                                autocommit=False, 
                                bind=database_engine)

def get_database():
    database = database_session()
    try:
        yield database
    finally:
        database.close()
# db_sessionが1リクエスト中のDB操作単位