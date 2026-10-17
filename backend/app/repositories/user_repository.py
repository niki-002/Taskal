# usersテーブルへのDBアクセス
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.auth import User


def get_by_subject(db: Session, auth_subject: str) -> User | None:
    return db.scalar(select(User).where(User.auth_subject == auth_subject))


def update_email(db: Session, user: User, email: str) -> User:
    user.email = email
    db.commit()
    db.refresh(user)
    return user


# 同時作成で一意制約に違反した場合は、先に作成されたユーザーを返す
def create(db: Session, user: User) -> User:
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = get_by_subject(db, user.auth_subject)
        if existing is None:
            raise
        return existing
    db.refresh(user)
    return user
