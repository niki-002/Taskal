# APIのURL定義
from fastapi import APIRouter

from app.core.pagination import Page, PageParamsDep
from app.schemas.schedule import (
    ScheduleCreate,
    ScheduleListParamsDep,
    ScheduleResponse,
    ScheduleUpdate,
)
from app.services.auth import CurrentUserDep
from app.services.schedule import ScheduleServiceDep


router = APIRouter(prefix="/schedules")


@router.get(
    "",
    status_code=200,
    response_model=Page[ScheduleResponse]
)
async def list_schedules(
    params: ScheduleListParamsDep,
    page: PageParamsDep,
    service: ScheduleServiceDep,
    current_user: CurrentUserDep
):
    return await service.list_schedules(params, page, current_user)


@router.post(
    "",
    status_code=201,
    response_model=ScheduleResponse
)
async def create_schedule(
    new_schedule: ScheduleCreate,
    service: ScheduleServiceDep,
    current_user: CurrentUserDep
):
    return await service.create_schedule(new_schedule, current_user)


@router.get(
    "/{schedule_id}",
    status_code=200,
    response_model=ScheduleResponse
)
async def get_schedule(
    schedule_id: int,
    service: ScheduleServiceDep,
    current_user: CurrentUserDep
):
    return await service.get_schedule(schedule_id, current_user)


@router.patch(
    "/{schedule_id}",
    status_code=200,
    response_model=ScheduleResponse
)
async def update_schedule(
    schedule_id: int,
    new_data: ScheduleUpdate,
    service: ScheduleServiceDep,
    current_user: CurrentUserDep
):
    return await service.update_schedule(schedule_id, new_data, current_user)


@router.delete(
    "/{schedule_id}",
    status_code=204,
)
async def delete_schedule(
    schedule_id: int,
    service: ScheduleServiceDep,
    current_user: CurrentUserDep
):
    await service.delete_schedule(schedule_id, current_user)
    return None
