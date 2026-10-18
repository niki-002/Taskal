from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


TRANSACTION_TYPES = ("income", "expense")


# 将来発生する予定の収入・支出（収支見込）
class PlannedTransaction(Base):
    __tablename__ = "planned_transactions"
    __table_args__ = (
        CheckConstraint(
            "type IN ('income', 'expense')",
            name="ck_planned_transactions_type",
        ),
        CheckConstraint("amount > 0", name="ck_planned_transactions_amount_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
        nullable=False
    )
    # Scheduleを削除しても金融履歴を残すため、NULLにする
    schedule_id: Mapped[int | None] = mapped_column(
        ForeignKey("schedules.id", ondelete="SET NULL"),
        index=True,
        nullable=True
    )
    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id"),
        index=True,
        nullable=True
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[int] = mapped_column(nullable=False)
    expected_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
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
