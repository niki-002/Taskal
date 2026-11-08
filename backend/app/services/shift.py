# kind=shiftの予定と連動するシフト（Shift）を扱う処理
from typing import Annotated

from fastapi import Depends

from app.core.errors import NotFoundError, ValidationError
from app.core.pagination import Page, PageParams
from app.models.auth import User
from app.models.schedule import Schedule
from app.models.shift import Shift
from app.repositories.planned_transaction import (
    PlannedTransactionRepository,
    PlannedTransactionRepositoryDep,
)
from app.repositories.shift import ShiftRepository, ShiftRepositoryDep
from app.schemas.schedule import EndAfterStartError
from app.schemas.shift import (
    BreakExceedsWorkingTimeError,
    ShiftCreate,
    ShiftListParams,
    ShiftResponse,
    ShiftUpdate,
)

SHIFT_NOT_FOUND = "shift not found."


class ShiftService:
    def __init__(
            self,
            repository: ShiftRepository,
            planned_transaction_repository: PlannedTransactionRepository,
    ):
        self.repository = repository
        self.planned_transaction_repository = planned_transaction_repository

    async def list_shifts(
            self,
            params: ShiftListParams,
            page: PageParams,
            current_user: User
    ) -> Page[ShiftResponse]:
        # カーソルは最後に返したシフトのschedule_idなので、そのシフトの start_at から続きを取得する
        after = None
        if page.after_id is not None:
            after = await self.repository.get_by_id(page.after_id, current_user.id)
            if after is None:
                raise ValidationError(details=[{"field": "cursor", "reason": "invalid_cursor"}])

        rows = await self.repository.list_page_in_period(
            current_user.id,
            params.from_at,
            params.to_at,
            page.limit,
            after=after,
        )
        return Page.from_rows(
            [self._to_response(row) for row in rows],
            page.limit,
            key=lambda item: item.schedule_id,
        )

    async def get_shift(self, schedule_id: int, current_user: User) -> ShiftResponse:
        return self._to_response(await self._get_own_shift(schedule_id, current_user))

    # ScheduleとShiftを同じトランザクションで作成する
    async def create_shift(self, new_shift: ShiftCreate, current_user: User) -> ShiftResponse:
        return self._to_response(await self.repository.add(
            Shift(
                **new_shift.model_dump(exclude={"schedule"}),
                schedule=Schedule(
                    user_id=current_user.id,
                    kind="shift",
                    **new_shift.schedule.model_dump(),
                ),
            )
        ))

    # ShiftとScheduleの項目を同じトランザクションで更新する
    async def update_shift(
            self,
            schedule_id: int,
            new_data: ShiftUpdate,
            current_user: User
    ) -> ShiftResponse:
        target = await self._get_own_shift(schedule_id, current_user)
        changes = new_data.model_dump(exclude_unset=True, exclude={"schedule"})
        schedule_changes = (
            new_data.schedule.model_dump(exclude_unset=True)
            if new_data.schedule is not None else {}
        )

        start_at = schedule_changes.get("start_at", target.schedule.start_at)
        end_at = schedule_changes.get("end_at", target.schedule.end_at)
        EndAfterStartError.check(start_at, end_at, prefix="schedule.")
        BreakExceedsWorkingTimeError.check(
            start_at,
            end_at,
            changes.get("break_minutes", target.break_minutes),
        )

        for field, value in changes.items():
            setattr(target, field, value)
        for field, value in schedule_changes.items():
            setattr(target.schedule, field, value)
        return self._to_response(await self.repository.save(target))

    # 未実績化の収支見込を削除してからShiftとScheduleを削除し、まとめて1回でcommitする
    async def delete_shift(self, schedule_id: int, current_user: User) -> None:
        target = await self._get_own_shift(schedule_id, current_user)
        await self.planned_transaction_repository.delete_unactualized_by_schedule(target.schedule_id)
        await self.repository.delete(target)

    async def _get_own_shift(self, schedule_id: int, current_user: User) -> Shift:
        return NotFoundError.require(
            await self.repository.get_by_id(schedule_id, current_user.id),
            SHIFT_NOT_FOUND
        )

    @staticmethod
    def _to_response(shift: Shift) -> ShiftResponse:
        return ShiftResponse.model_validate(shift)


def get_shift_service(
        repository: ShiftRepositoryDep,
        planned_transaction_repository: PlannedTransactionRepositoryDep,
) -> ShiftService:
    return ShiftService(repository, planned_transaction_repository)


ShiftServiceDep = Annotated[ShiftService, Depends(get_shift_service)]
