from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func, text, true
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


ACCOUNT_TYPES = ("cash", "bank", "e_money", "other")


# 履歴保護のため物理削除せず、is_active=falseにする
class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint(
            "type IN ('cash', 'bank', 'e_money', 'other')",
            name="ck_accounts_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    initial_balance: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        server_default=text("0")
    )
    is_active: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
        server_default=true()
    )
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
