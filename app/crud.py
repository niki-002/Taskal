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

def read_tasks(db: Session) -> list[Task]:
    return list(db.scalars(select(Task)).all())