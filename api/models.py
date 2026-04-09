<<<<<<< HEAD
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base

class Base(declarative_base):
=======
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase

# ORMモデルの親クラス
class Base(DeclarativeBase):
>>>>>>> 883a560 (ver4.0 モデル定義変更)
    pass

class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    done_flag: Mapped[bool] = mapped_column(nullable=False, default=False)