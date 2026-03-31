from fastapi import HTTPException
from sqlalchemy import select, delete
from sqlalchemy.orm import Session, session
from .models import Task
from .schemas import TaskCreate ,TaskCreateResponse, TaskReadResponse

def get_tasks(database: Session) -> list[Task]:
    return list(database.scalars(select(Task)).all())

def get_task(task_id: int, database: Session) -> Task:
    task = database.scalar(select(Task).where(Task.id == task_id))
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task

def create_task(new_task: TaskCreate, database: Session) -> Task:
    task = Task(**new_task.dict())
    database.add(task)
    database.commit()
    database.refresh(new_task)
    return new_task

def delete_task(deleted_task_id: int, database: Session) -> None:
    deleted_task = database.scalar(select(Task).where(Task.id == deleted_task_id))
    if deleted_task is None:
        raise HTTPException(status_code=404, detail="task not found")
    database.delete(deleted_task)
    database.commit()