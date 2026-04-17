# APIのURL定義
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.database import get_database
from api import crud
from api import schemas

router = APIRouter(prefix="/api/tasks")

@router.get("")
def get_tasks(database: Session = Depends(get_database)):
    return crud.get_tasks(database)

@router.get("/{task_id}")
def get_task(task_id: int, database: Session = Depends(get_database)):
    return crud.get_task(task_id, database)

@router.post("", status_code=201)
def create_task(new_task: schemas.TaskCreate, database: Session = Depends(get_database)):
    return crud.create_task(new_task, database)

@router.put("/{task_id}")
def update_task(task_id: int, new_data: schemas.TaskUpdate, database: Session = Depends(get_database)):
    return crud.update_task(task_id, new_data, database)

@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, database: Session = Depends(get_database)):
    task = crud.delete_task(task_id, database)
    if not task:
        raise HTTPException(status_code=404, detail="task not found.")
    return None 