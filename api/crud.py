from sqlalchemy import select
from sqlalchemy.orm import Session
from api.models import Task
from api.schemas import TaskCreate

def get_tasks(database: Session) -> list[Task]:
    return list(database.scalars(select(Task)).all())

def create_task(new_task: TaskCreate, database: Session) -> Task:
    task = Task(
        title = new_task.title,
        done_flag = False
    )
    database.add(task)
    database.commit()
    database.refresh(task)
    return task

def delete_task(deleted_task_id: int, database: Session) -> None:
    deleted_task = database.scalar(select(Task).where(Task.id == deleted_task_id))
    if deleted_task is None:
        return False
    database.delete(deleted_task)
    database.commit()
    return True