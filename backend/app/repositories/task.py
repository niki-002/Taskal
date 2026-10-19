# tasksテーブルへのDBアクセス
# NOTE: TaskはScheduleと同じschedule_idを主キーに持つため、所有者はScheduleで判定する
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.schedule import Schedule
from app.models.task import Task


# 非同期では遅延ロードができない（MissingGreenletになる）ため、Scheduleも一緒に読み込む
def _select_by_owner(owner_id: int):
    return (
        select(Task)
        .join(Task.schedule)
        .where(Schedule.user_id == owner_id)
        .options(selectinload(Task.schedule))
    )


async def list_by_owner(db: AsyncSession, owner_id: int) -> list[Task]:
    return list(await db.scalars(_select_by_owner(owner_id).order_by(Task.schedule_id)))


async def list_page_by_owner(
        db: AsyncSession,
        owner_id: int,
        limit: int,
        after_id: int | None = None,
) -> list[Task]:
    # 次ページの有無を判定するため limit+1 件取得する
    stmt = _select_by_owner(owner_id).order_by(Task.schedule_id).limit(limit + 1)
    if after_id is not None:
        stmt = stmt.where(Task.schedule_id > after_id)
    return list(await db.scalars(stmt))


async def get_by_id(db: AsyncSession, task_id: int, owner_id: int) -> Task | None:
    return await db.scalar(_select_by_owner(owner_id).where(Task.schedule_id == task_id))


# Taskに紐づくScheduleも同時に追加する
async def add(db: AsyncSession, task: Task) -> Task:
    db.add(task)
    await db.commit()
    return await _refresh(db, task)


async def save(db: AsyncSession, task: Task) -> Task:
    await db.commit()
    return await _refresh(db, task)


# Scheduleを削除すると、TaskはON DELETE CASCADEで削除される
async def delete(db: AsyncSession, task: Task) -> None:
    await db.delete(task.schedule)
    await db.commit()


# DB側で決まる値（Scheduleのcreated_at・updated_at など）を読み直す
# relationshipは名前を指定しないと読み直し後にアクセスしたとき遅延ロードになるため、scheduleも指定する
async def _refresh(db: AsyncSession, task: Task) -> Task:
    await db.refresh(task, ["due_date", "done_flag", "schedule"])
    return task
