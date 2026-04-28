# APIのURL定義
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Annotated

from api.db import get_db
from api.services import task_service
from api.schemas import task
from api.models.auth import User
from api.services.auth_service import get_current_active_user


router = APIRouter(prefix="/api/tasks")


@router.get(
    "",
    status_code=200,
    response_model=list[task.TaskResponse]
)
def get_tasks(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    return task_service.get_tasks(db, current_user)


@router.get(
    "/{task_id}",
    status_code=200,
    response_model=task.TaskResponse
)
def get_task(
    task_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    task =  task_service.get_task(
        task_id,
        db,
        current_user
    )
    if task is None:
        raise HTTPException(
            status_code=404,
            detail="task not found."
        )
    return task


@router.post(
    "",
    status_code=201,
    response_model=task.TaskResponse
)
def create_task(
    new_task: task.TaskCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    return task_service.create_task(
        new_task,
        db,
        current_user
    )


@router.patch(
    "/{task_id}",
    status_code=200,
    response_model=task.TaskResponse
)
def update_task(
    task_id: int,
    new_data: task.TaskUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    task = task_service.update_task(
        task_id,
        new_data,
        db,
        current_user
    )
    if task is None:
        raise HTTPException(
            status_code=404,
            detail="task not found."
        )
    return task


@router.delete(
    "/{task_id}",
    status_code=204,
)
def delete_task(
    task_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    task = task_service.delete_task(
        task_id,
        db,
        current_user
    )
    if not task:
        raise HTTPException(
            status_code=404,
            detail="task not found."
        )
    return None 