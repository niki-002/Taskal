# kind=taskの予定と連動するタスク（Task）を扱う処理
from typing import Annotated

from fastapi import Depends

from app.core.errors import NotFoundError, ValidationError
from app.core.pagination import Page, PageParams
from app.models.auth import User
from app.models.schedule import Schedule
from app.models.task import Task
from app.repositories.planned_transaction import (
    PlannedTransactionRepository,
    PlannedTransactionRepositoryDep,
)
from app.repositories.task import TaskRepository, TaskRepositoryDep
from app.schemas.schedule import EndAfterStartError
from app.schemas.task import TaskCreate, TaskListParams, TaskResponse, TaskUpdate

TASK_NOT_FOUND = "task not found."


class TaskService:
    def __init__(
            self,
            repository: TaskRepository,
            planned_transaction_repository: PlannedTransactionRepository,
    ):
        self.repository = repository
        self.planned_transaction_repository = planned_transaction_repository

    async def list_tasks(
            self,
            params: TaskListParams,
            page: PageParams,
            current_user: User
    ) -> Page[TaskResponse]:
        # カーソルは最後に返したタスクのschedule_idなので、そのタスクの due_date から続きを取得する
        after = None
        if page.after_id is not None:
            after = await self.repository.get_by_id(page.after_id, current_user.id)
            if after is None:
                raise ValidationError(details=[{"field": "cursor", "reason": "invalid_cursor"}])

        rows = await self.repository.list_page(
            current_user.id,
            page.limit,
            done=params.done,
            due_from=params.due_from,
            due_to=params.due_to,
            category=params.category,
            after=after,
        )
        return Page.from_rows(
            [self._to_response(row) for row in rows],
            page.limit,
            key=lambda item: item.schedule_id,
        )

    async def get_task(self, schedule_id: int, current_user: User) -> TaskResponse:
        return self._to_response(await self._get_own_task(schedule_id, current_user))

    # ScheduleとTaskを同じトランザクションで作成する
    async def create_task(self, new_task: TaskCreate, current_user: User) -> TaskResponse:
        return self._to_response(await self.repository.add(
            Task(
                due_date=new_task.due_date,
                done_flag=False,
                schedule=Schedule(
                    user_id=current_user.id,
                    kind="task",
                    **new_task.schedule.model_dump(),
                ),
            )
        ))

    # TaskとScheduleの項目を同じトランザクションで更新する
    async def update_task(
            self,
            schedule_id: int,
            new_data: TaskUpdate,
            current_user: User
    ) -> TaskResponse:
        target = await self._get_own_task(schedule_id, current_user)
        changes = new_data.model_dump(exclude_unset=True, exclude={"schedule"})
        schedule_changes = (
            new_data.schedule.model_dump(exclude_unset=True)
            if new_data.schedule is not None else {}
        )

        EndAfterStartError.check(
            schedule_changes.get("start_at", target.schedule.start_at),
            schedule_changes.get("end_at", target.schedule.end_at),
            prefix="schedule.",
        )

        for field, value in changes.items():
            setattr(target, field, value)
        for field, value in schedule_changes.items():
            setattr(target.schedule, field, value)
        return self._to_response(await self.repository.save(target))

    # 未実績化の収支見込を削除してからTaskとScheduleを削除し、まとめて1回でcommitする
    async def delete_task(self, schedule_id: int, current_user: User) -> None:
        target = await self._get_own_task(schedule_id, current_user)
        await self.planned_transaction_repository.delete_unactualized_by_schedule(target.schedule_id)
        await self.repository.delete(target)

    async def _get_own_task(self, schedule_id: int, current_user: User) -> Task:
        return NotFoundError.require(
            await self.repository.get_by_id(schedule_id, current_user.id),
            TASK_NOT_FOUND
        )

    @staticmethod
    def _to_response(task: Task) -> TaskResponse:
        return TaskResponse.model_validate(task)


def get_task_service(
        repository: TaskRepositoryDep,
        planned_transaction_repository: PlannedTransactionRepositoryDep,
) -> TaskService:
    return TaskService(repository, planned_transaction_repository)


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
