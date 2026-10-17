# tasksテーブルへのDBアクセス
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.task import Task


def list_by_owner(db: Session, owner_id: int) -> list[Task]:
    return list(db.scalars(select(Task).where(Task.owner_id == owner_id)))


def list_page_by_owner(
        db: Session,
        owner_id: int,
        limit: int,
        after_id: int | None = None,
) -> list[Task]:
    # 次ページの有無を判定するため limit+1 件取得する
    stmt = select(Task).where(Task.owner_id == owner_id).order_by(Task.id).limit(limit + 1)
    if after_id is not None:
        stmt = stmt.where(Task.id > after_id)
    return list(db.scalars(stmt))


def get_by_id(db: Session, task_id: int, owner_id: int) -> Task | None:
    return db.scalar(
        select(Task).where(Task.id == task_id, Task.owner_id == owner_id)
    )


def add(db: Session, task: Task) -> Task:
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def save(db: Session, task: Task) -> Task:
    db.commit()
    db.refresh(task)
    return task


def delete(db: Session, task: Task) -> None:
    db.delete(task)
    db.commit()
