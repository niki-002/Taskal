from sqlalchemy import Column, Integer, String, Boolean
from .db import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    done_flag = Column(Boolean, nullable=False, default=False)