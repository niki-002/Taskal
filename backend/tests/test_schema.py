from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Account,
    PlannedTransaction,
    Schedule,
    Shift,
    Task,
    Transaction,
    User,
)


START_AT = datetime(2026, 9, 15, 1, 0, tzinfo=timezone.utc)
END_AT = START_AT + timedelta(hours=8)


@pytest.fixture()
def db(migrated_engine):
    with Session(migrated_engine) as session:
        yield session


@pytest.fixture()
def user(db: Session) -> User:
    user = User(username="schema-user", auth_subject="auth0|schema-user")
    db.add(user)
    db.commit()
    return user


@pytest.fixture()
def account(db: Session, user: User) -> Account:
    account = Account(user_id=user.id, name="生活用口座", type="bank", initial_balance=1000)
    db.add(account)
    db.commit()
    return account


def make_schedule(user: User, **overrides) -> Schedule:
    values = {
        "user_id": user.id,
        "title": "カフェ勤務",
        "start_at": START_AT,
        "end_at": END_AT,
        "kind": "event",
    }
    values.update(overrides)
    return Schedule(**values)


def make_planned_transaction(user: User, **overrides) -> PlannedTransaction:
    values = {
        "user_id": user.id,
        "type": "income",
        "amount": 9100,
        "expected_date": date(2026, 9, 25),
    }
    values.update(overrides)
    return PlannedTransaction(**values)


def make_transaction(user: User, account: Account, **overrides) -> Transaction:
    values = {
        "user_id": user.id,
        "account_id": account.id,
        "type": "expense",
        "amount": 850,
        "source": "manual",
        "occurred_at": START_AT,
    }
    values.update(overrides)
    return Transaction(**values)


def assert_rejected(db: Session, record) -> None:
    db.add(record)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_defaults_are_set_by_db(db: Session, user: User):
    schedule = make_schedule(user, kind="task")
    schedule.task = Task(due_date=END_AT)
    account = Account(user_id=user.id, name="財布", type="cash")
    db.add_all([schedule, account])
    db.commit()

    assert schedule.task.done_flag is False
    assert schedule.created_at.tzinfo is not None
    assert schedule.updated_at.tzinfo is not None
    assert account.initial_balance == 0
    assert account.is_active is True


@pytest.mark.parametrize("kind", ["event", "task", "shift", "payment"])
def test_schedule_accepts_valid_kind(db: Session, user: User, kind: str):
    db.add(make_schedule(user, kind=kind))
    db.commit()


def test_schedule_rejects_invalid_kind(db: Session, user: User):
    assert_rejected(db, make_schedule(user, kind="meeting"))


@pytest.mark.parametrize("end_at", [START_AT, START_AT - timedelta(minutes=1)])
def test_schedule_rejects_end_at_not_after_start_at(db: Session, user: User, end_at: datetime):
    assert_rejected(db, make_schedule(user, end_at=end_at))


@pytest.mark.parametrize(
    "overrides",
    [{"hourly_wage": -1}, {"break_minutes": -1}],
)
def test_shift_rejects_negative_values(db: Session, user: User, overrides: dict):
    schedule = make_schedule(user, kind="shift")
    schedule.shift = Shift(**{"hourly_wage": 1300, "break_minutes": 60, **overrides})
    assert_rejected(db, schedule)


def test_account_rejects_invalid_type(db: Session, user: User):
    assert_rejected(db, Account(user_id=user.id, name="カード", type="credit"))


@pytest.mark.parametrize("overrides", [{"type": "transfer"}, {"amount": 0}, {"amount": -1}])
def test_planned_transaction_rejects_invalid_values(db: Session, user: User, overrides: dict):
    assert_rejected(db, make_planned_transaction(user, **overrides))


@pytest.mark.parametrize(
    "overrides",
    [{"type": "transfer"}, {"amount": 0}, {"amount": -1}, {"source": "import"}],
)
def test_transaction_rejects_invalid_values(
    db: Session,
    user: User,
    account: Account,
    overrides: dict,
):
    assert_rejected(db, make_transaction(user, account, **overrides))


def test_transaction_source_must_match_planned_transaction(
    db: Session,
    user: User,
    account: Account,
):
    planned = make_planned_transaction(user)
    db.add(planned)
    db.commit()

    assert_rejected(db, make_transaction(user, account, source="planned_transaction"))
    assert_rejected(
        db,
        make_transaction(user, account, source="manual", planned_transaction_id=planned.id),
    )


def test_planned_transaction_is_actualized_at_most_once(
    db: Session,
    user: User,
    account: Account,
):
    planned = make_planned_transaction(user)
    db.add(planned)
    db.commit()

    db.add(make_transaction(
        user,
        account,
        source="planned_transaction",
        planned_transaction_id=planned.id,
    ))
    db.commit()

    assert_rejected(db, make_transaction(
        user,
        account,
        source="planned_transaction",
        planned_transaction_id=planned.id,
    ))


def test_deleting_schedule_cascades_and_keeps_planned_transaction(db: Session, user: User):
    task_schedule = make_schedule(user, kind="task")
    task_schedule.task = Task(due_date=END_AT)
    shift_schedule = make_schedule(user, kind="shift")
    shift_schedule.shift = Shift(hourly_wage=1300, break_minutes=60)
    db.add_all([task_schedule, shift_schedule])
    db.flush()
    planned = make_planned_transaction(user, schedule_id=shift_schedule.id)
    db.add(planned)
    db.commit()
    planned_id = planned.id

    db.delete(task_schedule)
    db.delete(shift_schedule)
    db.commit()
    db.expire_all()

    assert db.scalars(select(Task)).all() == []
    assert db.scalars(select(Shift)).all() == []
    kept_planned = db.get(PlannedTransaction, planned_id)
    assert kept_planned is not None
    assert kept_planned.schedule_id is None
