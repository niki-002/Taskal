from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False
        )
    # Auth0のアクセストークンにメールアドレスが含まれない場合もあるためNULLを許可する
    email: Mapped[str | None] = mapped_column(
        unique=True,
        index=True,
        nullable=True
        )
    # Auth0のsub（例: "auth0|xxxxxxxx"）
    auth_subject: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
