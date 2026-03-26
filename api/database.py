from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "postgresql+psycopg2://taskal:taskalpass@localhost:5432/taskal"

db_engine = create_engine(DATABASE_URL, 
                          echo=True)

db_session = sessionmaker(autoflush=False, 
                          autocommit=False, 
                          bind=db_engine)

Base = declarative_base()

def get_db():
    try:
        yield db_session()
    finally:
        db_session().close()
# db_sessionが1リクエスト中のDB操作単位