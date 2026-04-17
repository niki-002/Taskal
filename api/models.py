# データベース構造の定義
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from datetime import date

# ORMモデルの親クラス
class Base(DeclarativeBase):
    pass

class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(1000))
    limit: Mapped[date] = mapped_column() 
    done_flag: Mapped[bool] = mapped_column(nullable=False, default=False)