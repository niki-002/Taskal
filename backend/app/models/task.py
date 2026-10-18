# データベース構造の定義
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .schedule import Schedule


# kind=taskのScheduleの拡張データ。schedule_idを主キー兼外部キーとして持つ
class Task(Base):
    __tablename__ = "tasks"

    schedule_id: Mapped[int] = mapped_column(
        ForeignKey("schedules.id", ondelete="CASCADE"),
        primary_key=True
    )
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    done_flag: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default=false()
    )

    schedule: Mapped["Schedule"] = relationship(back_populates="task")
