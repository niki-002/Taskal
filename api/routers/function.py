from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_database
from .. import crud
from ..schemas import TaskCreate, TaskCreateResponse, TaskReadResponse

router = APIRouter()

@router.get("/")
def get_tasks(db: Session = Depends(get_database)):
    return crud.get_tasks(db)

@router.get("/{task_id}", response_model=TaskReadResponse)
def get_task(task_id: int, db: Session = Depends(get_database)):
    return crud.get_task(task_id, db)

@router.post("/", response_model=TaskCreateResponse)
def create_task(new_task: TaskCreate, db: Session = Depends(get_database)):
    return crud.create_task(new_task, db)

@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_database)):
    return crud.delete_task(task_id, db)