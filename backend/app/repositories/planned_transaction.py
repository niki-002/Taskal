# planned_transactionsテーブルへのDBアクセス
from typing import Annotated

from fastapi import Depends
from sqlalchemy import delete, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.planned_transaction import PlannedTransaction
from app.models.transaction import Transaction


class PlannedTransactionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # Scheduleに紐づく未実績化（Transactionが作られていない）の収支見込を削除する
    # Scheduleの削除と同じトランザクションで確定させるため、ここではcommitしない
    async def delete_unactualized_by_schedule(self, schedule_id: int) -> None:
        actualized = exists(
            select(Transaction.id).where(Transaction.planned_transaction_id == PlannedTransaction.id)
        )
        await self.db.execute(
            delete(PlannedTransaction).where(
                PlannedTransaction.schedule_id == schedule_id,
                ~actualized,
            )
        )


def get_planned_transaction_repository(
        db: Annotated[AsyncSession, Depends(get_db)]
) -> PlannedTransactionRepository:
    return PlannedTransactionRepository(db)


PlannedTransactionRepositoryDep = Annotated[
    PlannedTransactionRepository,
    Depends(get_planned_transaction_repository),
]
