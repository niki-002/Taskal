# APIのURL定義
from fastapi import APIRouter

from app.core.pagination import Page, PageParamsDep
from app.schemas.task import TaskCreate, TaskListParamsDep, TaskResponse, TaskUpdate
from app.services.auth import CurrentUserDep
from app.services.task import TaskServiceDep


router = APIRouter(prefix="/tasks")


@router.get(
    "",
    status_code=200,
    response_model=Page[TaskResponse]
)
async def list_tasks(
    params: TaskListParamsDep,
    page: PageParamsDep,
    service: TaskServiceDep,
    current_user: CurrentUserDep
):
    return await service.list_tasks(params, page, current_user)


@router.post(
    "",
    status_code=201,
    response_model=TaskResponse
)
async def create_task(
    new_task: TaskCreate,
    service: TaskServiceDep,
    current_user: CurrentUserDep
):
    return await service.create_task(new_task, current_user)


@router.get(
    "/{schedule_id}",
    status_code=200,
    response_model=TaskResponse
)
async def get_task(
    schedule_id: int,
    service: TaskServiceDep,
    current_user: CurrentUserDep
):
    return await service.get_task(schedule_id, current_user)


@router.patch(
    "/{schedule_id}",
    status_code=200,
    response_model=TaskResponse
)
async def update_task(
    schedule_id: int,
    new_data: TaskUpdate,
    service: TaskServiceDep,
    current_user: CurrentUserDep
):
    return await service.update_task(schedule_id, new_data, current_user)


@router.delete(
    "/{schedule_id}",
    status_code=204,
)
async def delete_task(
    schedule_id: int,
    service: TaskServiceDep,
    current_user: CurrentUserDep
):
    await service.delete_task(schedule_id, current_user)
    return None
