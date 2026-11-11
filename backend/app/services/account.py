# 現金・銀行口座などの資産（Account）を扱う処理
from typing import Annotated, Sequence

from fastapi import Depends

from app.core.errors import NotFoundError
from app.core.pagination import Page, PageParams
from app.models.account import Account
from app.models.auth import User
from app.repositories.account import AccountRepository, AccountRepositoryDep
from app.schemas.account import (
    AccountCreate,
    AccountListParams,
    AccountResponse,
    AccountUpdate,
)

ACCOUNT_NOT_FOUND = "account not found."


class AccountService:
    def __init__(self, repository: AccountRepository):
        self.repository = repository

    async def list_accounts(
            self,
            params: AccountListParams,
            page: PageParams,
            current_user: User
    ) -> Page[AccountResponse]:
        rows = await self.repository.list_page(
            current_user.id,
            page.limit,
            is_active=params.is_active,
            after_id=page.after_id,
        )
        return Page.from_rows(await self._to_responses(rows), page.limit)

    async def get_account(self, account_id: int, current_user: User) -> AccountResponse:
        return await self._to_response(await self._get_own_account(account_id, current_user))

    async def create_account(self, new_account: AccountCreate, current_user: User) -> AccountResponse:
        return await self._to_response(await self.repository.add(
            Account(user_id=current_user.id, is_active=True, **new_account.model_dump())
        ))

    async def update_account(
            self,
            account_id: int,
            new_data: AccountUpdate,
            current_user: User
    ) -> AccountResponse:
        target = await self._get_own_account(account_id, current_user)
        for field, value in new_data.model_dump(exclude_unset=True).items():
            setattr(target, field, value)
        return await self._to_response(await self.repository.save(target))

    # 取引履歴を保護するため物理削除せず、is_active=false にする
    async def delete_account(self, account_id: int, current_user: User) -> None:
        target = await self._get_own_account(account_id, current_user)
        target.is_active = False
        await self.repository.save(target)

    async def _get_own_account(self, account_id: int, current_user: User) -> Account:
        return NotFoundError.require(
            await self.repository.get_by_id(account_id, current_user.id),
            ACCOUNT_NOT_FOUND
        )

    async def _to_response(self, account: Account) -> AccountResponse:
        return (await self._to_responses([account]))[0]

    # 資産ごとのTransaction合計を1回のクエリでまとめて取得し、現在残高を付けて返す
    async def _to_responses(self, accounts: Sequence[Account]) -> list[AccountResponse]:
        totals = await self.repository.sum_transactions([account.id for account in accounts])
        return [
            AccountResponse.from_account(
                account,
                self._current_balance(account.initial_balance, *totals.get(account.id, (0, 0))),
            )
            for account in accounts
        ]

    # 現在残高 = 初期残高 + incomeのTransaction合計 - expenseのTransaction合計
    @staticmethod
    def _current_balance(initial_balance: int, income: int, expense: int) -> int:
        return initial_balance + income - expense


def get_account_service(repository: AccountRepositoryDep) -> AccountService:
    return AccountService(repository)


AccountServiceDep = Annotated[AccountService, Depends(get_account_service)]
