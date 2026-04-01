from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import Task
from .schemas import TaskCreate, TaskReadResponse

def get_tasks(database: Session) -> list[TaskReadResponse]:
    return list(database.scalars(select(Task)).all())

def get_task(task_id: int, database: Session) -> TaskReadResponse:
    task = database.scalar(select(Task).where(Task.id == task_id))
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task

def create_task(new_task: TaskCreate, database: Session) -> Task:
    task = Task(
        title = new_task.title,
        done_flag = False
    )
    database.add(task)
    database.commit()
    database.refresh(task)
    return task

def delete_task(deleted_task_id: int, database: Session) -> None:
    deleted_task = database.scalar(select(Task).where(Task.id == deleted_task_id))
    if deleted_task is None:
        raise HTTPException(status_code=404, detail="task not found")
    database.delete(deleted_task)
    database.commit()