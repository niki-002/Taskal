from fastapi import HTTPException
from sqlalchemy import select, delete
from sqlalchemy.orm import Session, session
from .models import Task
import app.schemas as schemas

def create_task(new_task: schemas.TaskCreate, db: Session) -> Task:
    task = Task(**new_task.dict())
    db.add(task)
    db.commit()
    db.refresh(new_task)
    return new_task

def get_tasks(db: Session) -> list[Task]:
    return list(db.scalars(select(Task)).all())

def get_task(task_id: int, db: Session) -> Task:
    task = db.scalar(select(Task).where(Task.id == task_id))
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task

def delete_task(deleted_task_id: int, db: Session) -> None:
    deleted_task = db.scalar(select(Task).where(Task.id == deleted_task_id))
    if deleted_task is None:
        raise HTTPException(status_code=404, detail="task not found")
    db.delete(deleted_task)
    db.commit()