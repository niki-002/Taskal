# schedulesテーブルへのDBアクセス
from datetime import datetime
from typing import Annotated, Sequence

from fastapi import Depends
from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models.schedule import Schedule


class ScheduleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # 非同期では遅延ロードができない（MissingGreenletになる）ため、TaskとShiftも一緒に読み込む
    @staticmethod
    def _select_by_owner(owner_id: int):
        return (
            select(Schedule)
            .where(Schedule.user_id == owner_id)
            .options(selectinload(Schedule.task), selectinload(Schedule.shift))
        )

    async def get_by_id(self, schedule_id: int, owner_id: int) -> Schedule | None:
        return await self.db.scalar(
            self._select_by_owner(owner_id).where(Schedule.id == schedule_id)
        )

    # [from_at, to_at) と一部でも重なる予定を (start_at, id) の昇順で返す
    # 次ページの有無を判定するため limit+1 件取得し、after より後の予定から返す
    async def list_page_in_period(
            self,
            owner_id: int,
            from_at: datetime,
            to_at: datetime,
            limit: int,
            kinds: Sequence[str] = (),
            category: str | None = None,
            after: Schedule | None = None,
    ) -> list[Schedule]:
        stmt = (
            self._select_by_owner(owner_id)
            .where(Schedule.start_at < to_at, Schedule.end_at > from_at)
            .order_by(Schedule.start_at, Schedule.id)
            .limit(limit + 1)
        )
        if kinds:
            stmt = stmt.where(Schedule.kind.in_(kinds))
        if category is not None:
            stmt = stmt.where(Schedule.category == category)
        if after is not None:
            stmt = stmt.where(
                tuple_(Schedule.start_at, Schedule.id) > tuple_(after.start_at, after.id)
            )
        return list(await self.db.scalars(stmt))

    async def add(self, schedule: Schedule) -> Schedule:
        self.db.add(schedule)
        await self.db.commit()
        return await self._refresh(schedule)

    async def save(self, schedule: Schedule) -> Schedule:
        await self.db.commit()
        return await self._refresh(schedule)

    # TaskとShiftはON DELETE CASCADEで削除される
    # 同じセッションでcommitまでに行った操作（未実績化の収支見込の削除など）も同じトランザクションで確定する
    async def delete(self, schedule: Schedule) -> None:
        await self.db.delete(schedule)
        await self.db.commit()

    # DB側で決まる値（created_at・updated_at）を読み直す
    # relationshipは名前を指定しないと読み直し後にアクセスしたとき遅延ロードになるため、task・shiftも指定する
    async def _refresh(self, schedule: Schedule) -> Schedule:
        await self.db.refresh(schedule, ["created_at", "updated_at", "task", "shift"])
        return schedule


def get_schedule_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> ScheduleRepository:
    return ScheduleRepository(db)


ScheduleRepositoryDep = Annotated[ScheduleRepository, Depends(get_schedule_repository)]
