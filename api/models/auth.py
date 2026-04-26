from sqlalchemy.orm import Mapped, mapped_column

from .Base import Base


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(nullable=False)
    emailaddress: Mapped[str] = mapped_column(nullable=False)
    hashpass: Mapped[str] = mapped_column(nullable=False)
