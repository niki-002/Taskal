# データベース構造の定義
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import date

from .Base import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(
        String(200),
        index=True,
        nullable=False
        )
    description: Mapped[str] = mapped_column(String(1000))
    limit: Mapped[date] = mapped_column() 
    done_flag: Mapped[bool] = mapped_column(
        nullable=False,
        default=False
        )
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))  # ForeignKeyは引数に定められたカラムに存在する値だけを入れられるよう指定する役割を持つ。