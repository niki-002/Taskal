# APIのURL定義
from fastapi import APIRouter

from app.core.pagination import Page, PageParamsDep
from app.schemas.shift import ShiftCreate, ShiftListParamsDep, ShiftResponse, ShiftUpdate
from app.services.auth import CurrentUserDep
from app.services.shift import ShiftServiceDep


router = APIRouter(prefix="/shifts")


@router.get(
    "",
    status_code=200,
    response_model=Page[ShiftResponse]
)
async def list_shifts(
    params: ShiftListParamsDep,
    page: PageParamsDep,
    service: ShiftServiceDep,
    current_user: CurrentUserDep
):
    return await service.list_shifts(params, page, current_user)


@router.post(
    "",
    status_code=201,
    response_model=ShiftResponse
)
async def create_shift(
    new_shift: ShiftCreate,
    service: ShiftServiceDep,
    current_user: CurrentUserDep
):
    return await service.create_shift(new_shift, current_user)


@router.get(
    "/{schedule_id}",
    status_code=200,
    response_model=ShiftResponse
)
async def get_shift(
    schedule_id: int,
    service: ShiftServiceDep,
    current_user: CurrentUserDep
):
    return await service.get_shift(schedule_id, current_user)


@router.patch(
    "/{schedule_id}",
    status_code=200,
    response_model=ShiftResponse
)
async def update_shift(
    schedule_id: int,
    new_data: ShiftUpdate,
    service: ShiftServiceDep,
    current_user: CurrentUserDep
):
    return await service.update_shift(schedule_id, new_data, current_user)


@router.delete(
    "/{schedule_id}",
    status_code=204,
)
async def delete_shift(
    schedule_id: int,
    service: ShiftServiceDep,
    current_user: CurrentUserDep
):
    await service.delete_shift(schedule_id, current_user)
    return None
