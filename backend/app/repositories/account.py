# accountsテーブルへのDBアクセス
from typing import Annotated, Sequence

from fastapi import Depends
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.account import Account
from app.models.transaction import Transaction


class AccountRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _select_by_owner(owner_id: int):
        return select(Account).where(Account.user_id == owner_id)

    async def get_by_id(self, account_id: int, owner_id: int) -> Account | None:
        return await self.db.scalar(
            self._select_by_owner(owner_id).where(Account.id == account_id)
        )

    # id の昇順で返す。次ページの有無を判定するため limit+1 件取得し、after_id より後の資産から返す
    async def list_page(
            self,
            owner_id: int,
            limit: int,
            is_active: bool | None = None,
            after_id: int | None = None,
    ) -> list[Account]:
        stmt = self._select_by_owner(owner_id).order_by(Account.id).limit(limit + 1)
        if is_active is not None:
            stmt = stmt.where(Account.is_active == is_active)
        if after_id is not None:
            stmt = stmt.where(Account.id > after_id)
        return list(await self.db.scalars(stmt))

    # 資産ごとに income のTransaction合計と expense のTransaction合計を返す
    # Transactionがない資産は結果に含まれない
    async def sum_transactions(
            self,
            account_ids: Sequence[int],
    ) -> dict[int, tuple[int, int]]:
        if not account_ids:
            return {}

        def total_of(transaction_type: str):
            return func.coalesce(
                func.sum(case((Transaction.type == transaction_type, Transaction.amount), else_=0)),
                0,
            )

        rows = await self.db.execute(
            select(Transaction.account_id, total_of("income"), total_of("expense"))
            .where(Transaction.account_id.in_(account_ids))
            .group_by(Transaction.account_id)
        )
        return {account_id: (income, expense) for account_id, income, expense in rows}

    async def add(self, account: Account) -> Account:
        self.db.add(account)
        await self.db.commit()
        return await self._refresh(account)

    async def save(self, account: Account) -> Account:
        await self.db.commit()
        return await self._refresh(account)

    # DB側で決まる値（created_at・updated_at）を読み直す
    async def _refresh(self, account: Account) -> Account:
        await self.db.refresh(account, ["created_at", "updated_at"])
        return account


def get_account_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> AccountRepository:
    return AccountRepository(db)


AccountRepositoryDep = Annotated[AccountRepository, Depends(get_account_repository)]
