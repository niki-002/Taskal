from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database import get_database
import crud
from schemas import TaskCreate, TaskReadResponse

router = APIRouter()

@router.get("/tasks")
def get_tasks(database: Session = Depends(get_database)):
    return crud.get_tasks(database)

@router.get("/tasks/{task_id}", response_model=TaskReadResponse)
def get_task(task_id: int, database: Session = Depends(get_database)):
    return crud.get_task(task_id, database)

@router.post("/tasks")
def create_task(new_task: TaskCreate, database: Session = Depends(get_database)):
    return crud.create_task(new_task, database)

@router.delete("/tasks/{task_id}")
def delete_task(task_id: int, database: Session = Depends(get_database)):
    return crud.delete_task(task_id, database)