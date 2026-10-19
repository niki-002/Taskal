# usersテーブルへのDBアクセス
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.auth import User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_subject(self, auth_subject: str) -> User | None:
        return await self.db.scalar(select(User).where(User.auth_subject == auth_subject))

    async def get_by_username(self, username: str) -> User | None:
        return await self.db.scalar(select(User).where(User.username == username))

    # 一意制約に違反した場合はロールバックしてから例外を投げ直す
    async def save(self, user: User) -> User:
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise
        await self.db.refresh(user)
        return user

    async def update_email(self, user: User, email: str) -> User:
        user.email = email
        return await self.save(user)

    # 同時作成で一意制約に違反した場合は、先に作成されたユーザーを返す
    async def create(self, user: User) -> User:
        self.db.add(user)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            existing = await self.get_by_subject(user.auth_subject)
            if existing is None:
                raise
            return existing
        await self.db.refresh(user)
        return user


def get_user_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> UserRepository:
    return UserRepository(db)


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
