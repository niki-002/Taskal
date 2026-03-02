from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas import TaskCreateResponse, TaskCreate, TaskReadResponse
from app.db import get_db
import app.crud as crud
from app.models import Task

router = APIRouter()

@router.get("/tasks", response_model=list[TaskReadResponse])
def list_tasks(db: Session = Depends(get_db)):
    return crud.get_tasks(db)

@router.get("/tasks/task", response_model=TaskReadResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    return crud.get_task(task_id, db)

@router.post("/tasks", response_model=TaskCreateResponse)
def create_task(task_body: TaskCreate, db: Session = Depends(get_db)):
    return crud.create_task(task_body, db)    

@router.delete("/tasks")
def delete_task():
    pass