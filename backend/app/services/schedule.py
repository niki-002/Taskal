# 予定（Schedule）を扱う処理
from typing import Annotated

from fastapi import Depends

from app.core.errors import ValidationError
from app.core.pagination import Page, PageParams
from app.models.auth import User
from app.models.schedule import Schedule
from app.repositories.planned_transaction import (
    PlannedTransactionRepository,
    PlannedTransactionRepositoryDep,
)
from app.repositories.schedule import ScheduleRepository, ScheduleRepositoryDep
from app.schemas.schedule import (
    EndAfterStartError,
    ScheduleCreate,
    ScheduleListParams,
    ScheduleResponse,
    ScheduleUpdate,
)
from app.services.ownership import require_owned

SCHEDULE_NOT_FOUND = "schedule not found."


class ScheduleService:
    def __init__(
            self,
            repository: ScheduleRepository,
            planned_transaction_repository: PlannedTransactionRepository,
    ):
        self.repository = repository
        self.planned_transaction_repository = planned_transaction_repository

    async def list_schedules(
            self,
            params: ScheduleListParams,
            page: PageParams,
            current_user: User
    ) -> Page[ScheduleResponse]:
        # カーソルは最後に返した予定のIDなので、その予定の start_at から続きを取得する
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
            kinds=params.kinds,
            category=params.category,
            after=after,
        )
        return Page.from_rows([self._to_response(row) for row in rows], page.limit)

    async def get_schedule(self, schedule_id: int, current_user: User) -> ScheduleResponse:
        return self._to_response(await self._get_own_schedule(schedule_id, current_user))

    async def create_schedule(
            self,
            new_schedule: ScheduleCreate,
            current_user: User
    ) -> ScheduleResponse:
        return self._to_response(await self.repository.add(
            Schedule(user_id=current_user.id, **new_schedule.model_dump())
        ))

    async def update_schedule(
            self,
            schedule_id: int,
            new_data: ScheduleUpdate,
            current_user: User
    ) -> ScheduleResponse:
        target = await self._get_own_schedule(schedule_id, current_user)
        changes = new_data.model_dump(exclude_unset=True)

        # 片方だけ更新する場合も、更新後の値どうしで前後関係を確認する
        start_at = changes.get("start_at", target.start_at)
        end_at = changes.get("end_at", target.end_at)
        if end_at <= start_at:
            raise ValidationError(details=[EndAfterStartError.to_detail()])

        for field, value in changes.items():
            setattr(target, field, value)
        return self._to_response(await self.repository.save(target))

    # 未実績化の収支見込を削除してからScheduleを削除し、まとめて1回でcommitする
    # 実績化済みの収支見込はDBの ON DELETE SET NULL で schedule_id だけがnullになって残る
    async def delete_schedule(self, schedule_id: int, current_user: User) -> None:
        target = await self._get_own_schedule(schedule_id, current_user)
        await self.planned_transaction_repository.delete_unactualized_by_schedule(target.id)
        await self.repository.delete(target)

    async def _get_own_schedule(self, schedule_id: int, current_user: User) -> Schedule:
        return require_owned(
            await self.repository.get_by_id(schedule_id, current_user.id),
            SCHEDULE_NOT_FOUND
        )

    @staticmethod
    def _to_response(schedule: Schedule) -> ScheduleResponse:
        return ScheduleResponse.model_validate(schedule)


def get_schedule_service(
        repository: ScheduleRepositoryDep,
        planned_transaction_repository: PlannedTransactionRepositoryDep,
) -> ScheduleService:
    return ScheduleService(repository, planned_transaction_repository)


ScheduleServiceDep = Annotated[ScheduleService, Depends(get_schedule_service)]
