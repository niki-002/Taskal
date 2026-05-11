from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column
from .Base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False
        )
    email: Mapped[str] = mapped_column(
        unique=True,
        index=True,
        nullable=False
        )
    hashed_password: Mapped[str] = mapped_column(nullable=False)
    disabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
