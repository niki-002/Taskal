from sqlalchemy.orm import Session
from .models import Task
import app.schemas as schemas

def create_task(created_task: schemas.TaskCreate, db: Session) -> Task:
    new_task = Task(**create_task.dict())
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task