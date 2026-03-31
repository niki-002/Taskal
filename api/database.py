from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "postgresql+psycopg2://taskal:taskalpass@localhost:5432/taskal"

database_engine = create_engine(DATABASE_URL)

database_session = sessionmaker(autoflush=False, 
                                autocommit=False, 
                                bind=database_engine)

Base = declarative_base()

def get_database():
    try:
        yield database_session()
    finally:
        database_session().close()
# db_sessionが1リクエスト中のDB操作単位