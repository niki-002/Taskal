from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .schedule import Schedule


# kind=shiftのScheduleの拡張データ。schedule_idを主キー兼外部キーとして持つ
class Shift(Base):
    __tablename__ = "shifts"
    __table_args__ = (
        CheckConstraint("hourly_wage >= 0", name="ck_shifts_hourly_wage_non_negative"),
        CheckConstraint("break_minutes >= 0", name="ck_shifts_break_minutes_non_negative"),
    )

    schedule_id: Mapped[int] = mapped_column(
        ForeignKey("schedules.id", ondelete="CASCADE"),
        primary_key=True
    )
    hourly_wage: Mapped[int] = mapped_column(nullable=False)
    break_minutes: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        server_default=text("0")
    )
    workplace: Mapped[str | None] = mapped_column(String(200), nullable=True)

    schedule: Mapped["Schedule"] = relationship(back_populates="shift")
