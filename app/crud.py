from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, session
from .models import Task
import app.schemas as schemas

def create_task(created_task: schemas.TaskCreate, db: Session) -> Task:
    new_task = Task(**created_task.dict())
    db.add(new_task)
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