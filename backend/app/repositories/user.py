# usersテーブルへのDBアクセス
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.auth import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_subject(self, auth_subject: str) -> User | None:
        return self.db.scalar(select(User).where(User.auth_subject == auth_subject))

    def get_by_username(self, username: str) -> User | None:
        return self.db.scalar(select(User).where(User.username == username))

    # 一意制約に違反した場合はロールバックしてから例外を投げ直す
    def save(self, user: User) -> User:
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise
        self.db.refresh(user)
        return user

    def update_email(self, user: User, email: str) -> User:
        user.email = email
        return self.save(user)

    # 同時作成で一意制約に違反した場合は、先に作成されたユーザーを返す
    def create(self, user: User) -> User:
        self.db.add(user)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            existing = self.get_by_subject(user.auth_subject)
            if existing is None:
                raise
            return existing
        self.db.refresh(user)
        return user


def get_user_repository(db: Annotated[Session, Depends(get_db)]) -> UserRepository:
    return UserRepository(db)


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
