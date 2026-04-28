# アプリの処理 & データベース操作
from sqlalchemy import select
from sqlalchemy.orm import Session
from api.models.task import Task
from api.models.auth import User
from api.schemas import task


def get_tasks(
        db: Session,
        current_user: User
) -> list[task.TaskResponse]:
    
    owner_id = current_user.id
    tasks = list(
        db.scalars(
            select(Task)
            .where(Task.owner_id == owner_id)
        )
    )
    return tasks


def get_task(
        task_id: int,
        db: Session,
        current_user: User
) -> task.TaskResponse | None:
    
    owner_id = current_user.id
    task = db.scalar(
        select(Task)
        .where(
            Task.id == task_id,
            Task.owner_id == owner_id
        )
    )
    if task is None:
        return None
    return task


def create_task(
        new_task: task.TaskCreate,
        db: Session,
        current_user: User
) -> task.TaskResponse:
    
    task = Task(
        title = new_task.title,
        description = new_task.description,
        limit = new_task.limit,
        done_flag = False,
        owner_id = current_user.id
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_done_flag(
        task_id: int,
        db: Session,
        current_user: User
) -> task.TaskResponse | None:
    
    owner_id = current_user.id
    task = db.scalar(
        select(Task)
        .where(
            Task.id == task_id,
            Task.owner_id == owner_id
        )
    )
    if task is None:
        return None
    
    if task.done_flag is False:
        task.done_flag = True
        db.commit()
        db.refresh(task)
    else:
        task.done_flag = False
        db.commit()
        db.refresh(task) 
    return task


def update_task(
        task_id: int,
        new_data: task.TaskUpdate,
        db: Session,
        current_user: User
) -> task.TaskResponse | None:

    owner_id = current_user.id
    task = db.scalar(
        select(Task)
        .where(
            Task.id == task_id,
            Task.owner_id == owner_id
        )
    )
    if task is None:
        return None
    
    task = Task(
        title = new_data.title,
        description = new_data.description,
        limit = new_data.limit
    )
    db.commit()
    db.refresh(task)
    return task


def delete_task(
        deleted_task_id: int,
        db: Session,
        current_user: User
) -> bool:

    owner_id = current_user.id
    deleted_task = db.scalar(
        select(Task)
        .where(
            Task.id == deleted_task_id,
            Task.owner_id == owner_id
        )
    )
    if deleted_task is None:
        return False
    db.delete(deleted_task)
    db.commit()
    return True