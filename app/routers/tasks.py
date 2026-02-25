from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas import TaskCreateResponse, TaskCreate, TaskReadResponse
from app.db import get_db
import app.crud as crud

router = APIRouter()

@router.get("/tasks", response_model=list[TaskReadResponse])
def list_tasks(db: Session = Depends(get_db)):
    return crud.read_tasks(db)

@router.get("/tasks")
def list_task():
    pass

@router.post("/tasks", response_model=TaskCreateResponse)
def create_task(task_body: TaskCreate, db: Session = Depends(get_db)):
    return crud.create_task(task_body, db)    

@router.delete("/tasks")
def delete_task():
    pass