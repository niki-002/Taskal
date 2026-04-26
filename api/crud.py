# データベース操作
from sqlalchemy import select
from sqlalchemy.orm import Session
from api.models.task import Task
from api.schemas import task

def create_task(new_task: task.TaskCreate, database: Session) -> task.CreatedTask:
    task = Task(
        title = new_task.title,
        description = new_task.description,
        limit = new_task.limit,
        done_flag = False
    )
    database.add(task)
    database.commit()
    database.refresh(task)
    return task

def get_tasks(database: Session) -> list[task.ReadTaskList]:
    return list(database.scalars(select(Task)).all())

def get_task(task_id: int, database: Session) -> task.ReadTask:
    task = database.scalar(select(Task).where(Task.id == task_id))
    return task

def update_task(task_id: int, new_data: task.TaskUpdate, database: Session) -> task.UpdatedTask:
    task = database.scalar(select(Task).where(Task.id == task_id))
    task = Task(
        title = new_data.title,
        description = new_data.description,
        limit = new_data.limit
    )
    database.commit()
    database.refresh(task)
    return task

def delete_task(deleted_task_id: int, database: Session) -> task.DeletedTask:
    deleted_task = database.scalar(select(Task).where(Task.id == deleted_task_id))
    if deleted_task is None:
        return False
    database.delete(deleted_task)
    database.commit()
    return True