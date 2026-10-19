# APIのURL定義
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.db import get_db
from app.services import task as task_service
from app.schemas import task
from app.models.auth import User
from app.services.auth import get_current_user


router = APIRouter(prefix="/tasks")


@router.get(
    "",
    status_code=200,
    response_model=list[task.TaskResponse]
)
async def get_tasks(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    return await task_service.get_tasks(db, current_user)


@router.get(
    "/{task_id}",
    status_code=200,
    response_model=task.TaskResponse
)
async def get_task(
    task_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    return await task_service.get_task(
        task_id,
        db,
        current_user
    )


@router.post(
    "",
    status_code=201,
    response_model=task.TaskResponse
)
async def create_task(
    new_task: task.TaskCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    return await task_service.create_task(
        new_task,
        db,
        current_user
    )


@router.put(
    "/{task_id}",
    status_code=200,
    response_model=task.TaskResponse
)
async def update_task(
    task_id: int,
    new_data: task.TaskUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    return await task_service.update_task(
        task_id,
        new_data,
        db,
        current_user
    )


@router.delete(
    "/{task_id}",
    status_code=204,
)
async def delete_task(
    task_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    await task_service.delete_task(
        task_id,
        db,
        current_user
    )
    return None 