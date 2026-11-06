# tasksテーブルへのDBアクセス
# NOTE: TaskはScheduleと同じschedule_idを主キーに持つため、所有者はScheduleで判定する
from datetime import datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models.schedule import Schedule
from app.models.task import Task


class TaskRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # 非同期では遅延ロードができない（MissingGreenletになる）ため、Scheduleも一緒に読み込む
    @staticmethod
    def _select_by_owner(owner_id: int):
        return (
            select(Task)
            .join(Task.schedule)
            .where(Schedule.user_id == owner_id)
            .options(selectinload(Task.schedule))
        )

    async def get_by_id(self, schedule_id: int, owner_id: int) -> Task | None:
        return await self.db.scalar(
            self._select_by_owner(owner_id).where(Task.schedule_id == schedule_id)
        )

    # 絞り込んだタスクを (due_date, schedule_id) の昇順で返す
    # 次ページの有無を判定するため limit+1 件取得し、after より後のタスクから返す
    async def list_page(
            self,
            owner_id: int,
            limit: int,
            done: bool | None = None,
            due_from: datetime | None = None,
            due_to: datetime | None = None,
            category: str | None = None,
            after: Task | None = None,
    ) -> list[Task]:
        stmt = (
            self._select_by_owner(owner_id)
            .order_by(Task.due_date, Task.schedule_id)
            .limit(limit + 1)
        )
        if done is not None:
            stmt = stmt.where(Task.done_flag == done)
        if due_from is not None:
            stmt = stmt.where(Task.due_date >= due_from)
        if due_to is not None:
            stmt = stmt.where(Task.due_date <= due_to)
        if category is not None:
            stmt = stmt.where(Schedule.category == category)
        if after is not None:
            stmt = stmt.where(
                tuple_(Task.due_date, Task.schedule_id) > tuple_(after.due_date, after.schedule_id)
            )
        return list(await self.db.scalars(stmt))

    # Taskに紐づくScheduleも同時に追加し、1回のcommit（1つのトランザクション）で確定する
    async def add(self, task: Task) -> Task:
        self.db.add(task)
        await self.db.commit()
        return await self._refresh(task)

    # TaskとScheduleの変更をまとめて1回でcommitする
    async def save(self, task: Task) -> Task:
        await self.db.commit()
        return await self._refresh(task)

    # Scheduleを削除すると、TaskはON DELETE CASCADEで削除される
    # 同じセッションでcommitまでに行った操作（未実績化の収支見込の削除など）も同じトランザクションで確定する
    async def delete(self, task: Task) -> None:
        await self.db.delete(task.schedule)
        await self.db.commit()

    # DB側で決まる値（Scheduleのcreated_at・updated_at）を読み直す
    async def _refresh(self, task: Task) -> Task:
        await self.db.refresh(task.schedule, ["created_at", "updated_at"])
        return task


def get_task_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> TaskRepository:
    return TaskRepository(db)


TaskRepositoryDep = Annotated[TaskRepository, Depends(get_task_repository)]
