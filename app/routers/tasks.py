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

@router.get("/tasks/{task_id}", response_model=TaskReadResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    return crud.get_task(task_id, db)

@router.post("/tasks/create_task", response_model=TaskCreateResponse)
def create_task(task_body: TaskCreate, db: Session = Depends(get_db)):
    return crud.create_task(task_body, db)    

@router.delete("/tasks/{deleted_task_id}")
def delete_task(deleted_task_id: int, db: Session = Depends(get_db)):
    crud.delete_task(deleted_task_id, db)
    return {"deleted": "タスクは削除されました。"}