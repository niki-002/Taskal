# tasksテーブルへのDBアクセス
# NOTE: TaskはScheduleと同じschedule_idを主キーに持つため、所有者はScheduleで判定する
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.schedule import Schedule
from app.models.task import Task


def _select_by_owner(owner_id: int):
    return select(Task).join(Task.schedule).where(Schedule.user_id == owner_id)


def list_by_owner(db: Session, owner_id: int) -> list[Task]:
    return list(db.scalars(_select_by_owner(owner_id).order_by(Task.schedule_id)))


def list_page_by_owner(
        db: Session,
        owner_id: int,
        limit: int,
        after_id: int | None = None,
) -> list[Task]:
    # 次ページの有無を判定するため limit+1 件取得する
    stmt = _select_by_owner(owner_id).order_by(Task.schedule_id).limit(limit + 1)
    if after_id is not None:
        stmt = stmt.where(Task.schedule_id > after_id)
    return list(db.scalars(stmt))


def get_by_id(db: Session, task_id: int, owner_id: int) -> Task | None:
    return db.scalar(_select_by_owner(owner_id).where(Task.schedule_id == task_id))


# Taskに紐づくScheduleも同時に追加する
def add(db: Session, task: Task) -> Task:
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def save(db: Session, task: Task) -> Task:
    db.commit()
    db.refresh(task)
    return task


# Scheduleを削除すると、TaskはON DELETE CASCADEで削除される
def delete(db: Session, task: Task) -> None:
    db.delete(task.schedule)
    db.commit()
