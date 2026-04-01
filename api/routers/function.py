from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_database
import crud
from schemas import TaskCreate, TaskReadResponse

router = APIRouter(prefix="/api/tasks")

@router.get("")
def get_tasks(database: Session = Depends(get_database)):
    return crud.get_tasks(database)

@router.get("/{task_id}", response_model=TaskReadResponse)
def get_task(task_id: int, database: Session = Depends(get_database)):
    task = crud.get_task(task_id, database)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task

@router.post("")
def create_task(new_task: TaskCreate, database: Session = Depends(get_database)):
    return crud.create_task(new_task, database)

@router.delete("/{task_id}")
def delete_task(task_id: int, database: Session = Depends(get_database)):
    task = crud.delete_task(task_id, database)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return None 