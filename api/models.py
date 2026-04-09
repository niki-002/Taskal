from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase

# ORMモデルの親クラス
class Base(DeclarativeBase):
    pass

class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    done_flag: Mapped[bool] = mapped_column(nullable=False, default=False)