from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .shift import Shift
    from .task import Task


# アプリの内部処理を決める種別
SCHEDULE_KINDS = ("event", "task", "shift", "payment")


class Schedule(Base):
    __tablename__ = "schedules"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('event', 'task', 'shift', 'payment')",
            name="ck_schedules_kind",
        ),
        CheckConstraint("end_at > start_at", name="ck_schedules_end_after_start"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
        nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    # ユーザーが自由に付けられる分類
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # TaskとShiftはDB側のON DELETE CASCADEで削除する
    task: Mapped["Task | None"] = relationship(
        back_populates="schedule",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    shift: Mapped["Shift | None"] = relationship(
        back_populates="schedule",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
