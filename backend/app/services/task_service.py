# アプリの処理
from sqlalchemy.orm import Session
from app.models.task import Task
from app.models.auth import User
from app.repositories import task_repository
from app.schemas import task
from app.services.ownership import require_owned

TASK_NOT_FOUND = "task not found."


def get_tasks(
        db: Session,
        current_user: User
) -> list[Task]:
    return task_repository.list_by_owner(db, current_user.id)


def get_task(
        task_id: int,
        db: Session,
        current_user: User
) -> Task:
    return require_owned(
        task_repository.get_by_id(db, task_id, current_user.id),
        TASK_NOT_FOUND
    )


def create_task(
        new_task: task.TaskCreate,
        db: Session,
        current_user: User
) -> Task:
    return task_repository.add(
        db,
        Task(
            title=new_task.title,
            description=new_task.description,
            limit=new_task.limit,
            done_flag=False,
            owner_id=current_user.id
        )
    )


def update_done_flag(
        task_id: int,
        db: Session,
        current_user: User
) -> Task:
    target = get_task(task_id, db, current_user)
    target.done_flag = not target.done_flag
    return task_repository.save(db, target)


def update_task(
        task_id: int,
        new_data: task.TaskUpdate,
        db: Session,
        current_user: User
) -> Task:
    target = get_task(task_id, db, current_user)
    target.title = new_data.title
    target.description = new_data.description
    target.limit = new_data.limit
    return task_repository.save(db, target)


def delete_task(
        deleted_task_id: int,
        db: Session,
        current_user: User
) -> None:
    task_repository.delete(db, get_task(deleted_task_id, db, current_user))
