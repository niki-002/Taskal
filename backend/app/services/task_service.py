# アプリの処理
# NOTE: v2のスキーマ上でv1のAPI仕様（limitを日付で扱う）を維持する暫定実装。
#       Schedule連動の仕様には #29 で置き換える。
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy.orm import Session
from app.models.auth import User
from app.models.schedule import Schedule
from app.models.task import Task
from app.repositories import task_repository
from app.schemas import task
from app.services.ownership import require_owned

TASK_NOT_FOUND = "task not found."


# limit（日付）はUTCの0時を期限とし、その日1日分のScheduleとして保存する
def _limit_to_due_date(limit: date) -> datetime:
    return datetime.combine(limit, time.min, tzinfo=timezone.utc)


def to_response(target: Task) -> task.TaskResponse:
    schedule = target.schedule
    return task.TaskResponse(
        id=schedule.id,
        owner_id=schedule.user_id,
        title=schedule.title,
        description=schedule.description or "",
        limit=target.due_date.astimezone(timezone.utc).date(),
        done_flag=target.done_flag,
    )


def _get_own_task(
        task_id: int,
        db: Session,
        current_user: User
) -> Task:
    return require_owned(
        task_repository.get_by_id(db, task_id, current_user.id),
        TASK_NOT_FOUND
    )


def get_tasks(
        db: Session,
        current_user: User
) -> list[task.TaskResponse]:
    return [
        to_response(target)
        for target in task_repository.list_by_owner(db, current_user.id)
    ]


def get_task(
        task_id: int,
        db: Session,
        current_user: User
) -> task.TaskResponse:
    return to_response(_get_own_task(task_id, db, current_user))


def create_task(
        new_task: task.TaskCreate,
        db: Session,
        current_user: User
) -> task.TaskResponse:
    due_date = _limit_to_due_date(new_task.limit)
    return to_response(task_repository.add(
        db,
        Task(
            due_date=due_date,
            done_flag=False,
            schedule=Schedule(
                user_id=current_user.id,
                title=new_task.title,
                description=new_task.description,
                start_at=due_date,
                end_at=due_date + timedelta(days=1),
                kind="task",
            )
        )
    ))


def update_done_flag(
        task_id: int,
        db: Session,
        current_user: User
) -> task.TaskResponse:
    target = _get_own_task(task_id, db, current_user)
    target.done_flag = not target.done_flag
    return to_response(task_repository.save(db, target))


def update_task(
        task_id: int,
        new_data: task.TaskUpdate,
        db: Session,
        current_user: User
) -> task.TaskResponse:
    target = _get_own_task(task_id, db, current_user)
    due_date = _limit_to_due_date(new_data.limit)
    target.schedule.title = new_data.title
    target.schedule.description = new_data.description
    target.schedule.start_at = due_date
    target.schedule.end_at = due_date + timedelta(days=1)
    target.due_date = due_date
    return to_response(task_repository.save(db, target))


def delete_task(
        deleted_task_id: int,
        db: Session,
        current_user: User
) -> None:
    task_repository.delete(db, _get_own_task(deleted_task_id, db, current_user))
