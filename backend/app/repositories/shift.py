# shiftsテーブルへのDBアクセス
# NOTE: ShiftはScheduleと同じschedule_idを主キーに持つため、所有者はScheduleで判定する
from datetime import datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models.schedule import Schedule
from app.models.shift import Shift


class ShiftRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # 非同期では遅延ロードができない（MissingGreenletになる）ため、Scheduleも一緒に読み込む
    @staticmethod
    def _select_by_owner(owner_id: int):
        return (
            select(Shift)
            .join(Shift.schedule)
            .where(Schedule.user_id == owner_id)
            .options(selectinload(Shift.schedule))
        )

    async def get_by_id(self, schedule_id: int, owner_id: int) -> Shift | None:
        return await self.db.scalar(
            self._select_by_owner(owner_id).where(Shift.schedule_id == schedule_id)
        )

    # [from_at, to_at) と一部でも重なるシフトを (start_at, schedule_id) の昇順で返す
    # 次ページの有無を判定するため limit+1 件取得し、after より後のシフトから返す
    async def list_page_in_period(
            self,
            owner_id: int,
            from_at: datetime,
            to_at: datetime,
            limit: int,
            after: Shift | None = None,
    ) -> list[Shift]:
        stmt = (
            self._select_by_owner(owner_id)
            .where(Schedule.start_at < to_at, Schedule.end_at > from_at)
            .order_by(Schedule.start_at, Shift.schedule_id)
            .limit(limit + 1)
        )
        if after is not None:
            stmt = stmt.where(
                tuple_(Schedule.start_at, Shift.schedule_id)
                > tuple_(after.schedule.start_at, after.schedule_id)
            )
        return list(await self.db.scalars(stmt))

    # Shiftに紐づくScheduleも同時に追加し、1回のcommit（1つのトランザクション）で確定する
    async def add(self, shift: Shift) -> Shift:
        self.db.add(shift)
        await self.db.commit()
        return await self._refresh(shift)

    # ShiftとScheduleの変更をまとめて1回でcommitする
    async def save(self, shift: Shift) -> Shift:
        await self.db.commit()
        return await self._refresh(shift)

    # Scheduleを削除すると、ShiftはON DELETE CASCADEで削除される
    # 同じセッションでcommitまでに行った操作（未実績化の収支見込の削除など）も同じトランザクションで確定する
    async def delete(self, shift: Shift) -> None:
        await self.db.delete(shift.schedule)
        await self.db.commit()

    # DB側で決まる値（Scheduleのcreated_at・updated_at）を読み直す
    async def _refresh(self, shift: Shift) -> Shift:
        await self.db.refresh(shift.schedule, ["created_at", "updated_at"])
        return shift


def get_shift_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> ShiftRepository:
    return ShiftRepository(db)


ShiftRepositoryDep = Annotated[ShiftRepository, Depends(get_shift_repository)]
