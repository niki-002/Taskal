from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


TRANSACTION_SOURCES = ("manual", "schedule", "planned_transaction")


# 実際に発生した収入・支出（収支実績）。金額は常に正数で、加算・減算はtypeで判断する
class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint(
            "type IN ('income', 'expense')",
            name="ck_transactions_type",
        ),
        CheckConstraint(
            "source IN ('manual', 'schedule', 'planned_transaction')",
            name="ck_transactions_source",
        ),
        CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
        # 個別登録（manual）のときだけ収支見込を持たない
        CheckConstraint(
            "(source = 'manual') = (planned_transaction_id IS NULL)",
            name="ck_transactions_source_matches_planned_transaction",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
        nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"),
        index=True,
        nullable=False
    )
    # 1つの収支見込から作れる実績は最大1件
    planned_transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("planned_transactions.id"),
        unique=True,
        nullable=True
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[int] = mapped_column(nullable=False)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
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
