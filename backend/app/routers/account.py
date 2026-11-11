# APIのURL定義
from fastapi import APIRouter

from app.core.pagination import Page, PageParamsDep
from app.schemas.account import (
    AccountCreate,
    AccountListParamsDep,
    AccountResponse,
    AccountUpdate,
)
from app.services.account import AccountServiceDep
from app.services.auth import CurrentUserDep


router = APIRouter(prefix="/accounts")


@router.get(
    "",
    status_code=200,
    response_model=Page[AccountResponse]
)
async def list_accounts(
    params: AccountListParamsDep,
    page: PageParamsDep,
    service: AccountServiceDep,
    current_user: CurrentUserDep
):
    return await service.list_accounts(params, page, current_user)


@router.post(
    "",
    status_code=201,
    response_model=AccountResponse
)
async def create_account(
    new_account: AccountCreate,
    service: AccountServiceDep,
    current_user: CurrentUserDep
):
    return await service.create_account(new_account, current_user)


@router.get(
    "/{account_id}",
    status_code=200,
    response_model=AccountResponse
)
async def get_account(
    account_id: int,
    service: AccountServiceDep,
    current_user: CurrentUserDep
):
    return await service.get_account(account_id, current_user)


@router.patch(
    "/{account_id}",
    status_code=200,
    response_model=AccountResponse
)
async def update_account(
    account_id: int,
    new_data: AccountUpdate,
    service: AccountServiceDep,
    current_user: CurrentUserDep
):
    return await service.update_account(account_id, new_data, current_user)


@router.delete(
    "/{account_id}",
    status_code=204,
)
async def delete_account(
    account_id: int,
    service: AccountServiceDep,
    current_user: CurrentUserDep
):
    await service.delete_account(account_id, current_user)
    return None
