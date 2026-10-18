"""create v2 schema

Revision ID: b4e7d2c9a1f3
Revises: 8f3c2a1d9b7e
Create Date: 2026-10-18 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4e7d2c9a1f3'
down_revision: Union[str, Sequence[str], None] = '8f3c2a1d9b7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 旧tasksは新しいschedules・tasksへデータを移してから削除する
    op.drop_index(op.f('ix_tasks_title'), table_name='tasks')
    op.rename_table('tasks', 'legacy_tasks')
    # 新しいtasksの主キー名と衝突しないよう、旧テーブルの主キーとシーケンスも改名する
    op.execute("ALTER INDEX tasks_pkey RENAME TO legacy_tasks_pkey")
    op.execute("ALTER SEQUENCE tasks_id_seq RENAME TO legacy_tasks_id_seq")

    op.create_table('schedules',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('description', sa.String(length=2000), nullable=True),
    sa.Column('start_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('end_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('category', sa.String(length=50), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("kind IN ('event', 'task', 'shift', 'payment')", name='ck_schedules_kind'),
    sa.CheckConstraint('end_at > start_at', name='ck_schedules_end_after_start'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_schedules_user_id'), 'schedules', ['user_id'], unique=False)
    op.create_index(op.f('ix_schedules_start_at'), 'schedules', ['start_at'], unique=False)

    op.create_table('tasks',
    sa.Column('schedule_id', sa.Integer(), nullable=False),
    sa.Column('due_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('done_flag', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.ForeignKeyConstraint(['schedule_id'], ['schedules.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('schedule_id')
    )
    op.create_index(op.f('ix_tasks_due_date'), 'tasks', ['due_date'], unique=False)

    op.create_table('shifts',
    sa.Column('schedule_id', sa.Integer(), nullable=False),
    sa.Column('hourly_wage', sa.Integer(), nullable=False),
    sa.Column('break_minutes', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('workplace', sa.String(length=200), nullable=True),
    sa.CheckConstraint('hourly_wage >= 0', name='ck_shifts_hourly_wage_non_negative'),
    sa.CheckConstraint('break_minutes >= 0', name='ck_shifts_break_minutes_non_negative'),
    sa.ForeignKeyConstraint(['schedule_id'], ['schedules.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('schedule_id')
    )

    op.create_table('accounts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('type', sa.String(length=20), nullable=False),
    sa.Column('initial_balance', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("type IN ('cash', 'bank', 'e_money', 'other')", name='ck_accounts_type'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_accounts_user_id'), 'accounts', ['user_id'], unique=False)

    op.create_table('planned_transactions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('schedule_id', sa.Integer(), nullable=True),
    sa.Column('account_id', sa.Integer(), nullable=True),
    sa.Column('type', sa.String(length=20), nullable=False),
    sa.Column('amount', sa.Integer(), nullable=False),
    sa.Column('expected_date', sa.Date(), nullable=False),
    sa.Column('description', sa.String(length=1000), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("type IN ('income', 'expense')", name='ck_planned_transactions_type'),
    sa.CheckConstraint('amount > 0', name='ck_planned_transactions_amount_positive'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['schedule_id'], ['schedules.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_planned_transactions_user_id'), 'planned_transactions', ['user_id'], unique=False)
    op.create_index(op.f('ix_planned_transactions_schedule_id'), 'planned_transactions', ['schedule_id'], unique=False)
    op.create_index(op.f('ix_planned_transactions_account_id'), 'planned_transactions', ['account_id'], unique=False)
    op.create_index(op.f('ix_planned_transactions_expected_date'), 'planned_transactions', ['expected_date'], unique=False)

    op.create_table('transactions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=False),
    sa.Column('planned_transaction_id', sa.Integer(), nullable=True),
    sa.Column('type', sa.String(length=20), nullable=False),
    sa.Column('amount', sa.Integer(), nullable=False),
    sa.Column('category', sa.String(length=50), nullable=True),
    sa.Column('description', sa.String(length=1000), nullable=True),
    sa.Column('source', sa.String(length=30), nullable=False),
    sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("type IN ('income', 'expense')", name='ck_transactions_type'),
    sa.CheckConstraint("source IN ('manual', 'schedule', 'planned_transaction')", name='ck_transactions_source'),
    sa.CheckConstraint('amount > 0', name='ck_transactions_amount_positive'),
    sa.CheckConstraint("(source = 'manual') = (planned_transaction_id IS NULL)", name='ck_transactions_source_matches_planned_transaction'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
    sa.ForeignKeyConstraint(['planned_transaction_id'], ['planned_transactions.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('planned_transaction_id')
    )
    op.create_index(op.f('ix_transactions_user_id'), 'transactions', ['user_id'], unique=False)
    op.create_index(op.f('ix_transactions_account_id'), 'transactions', ['account_id'], unique=False)
    op.create_index(op.f('ix_transactions_occurred_at'), 'transactions', ['occurred_at'], unique=False)

    # 旧tasksのlimit（日付）はUTCの0時を期限とし、その日1日分のScheduleにする
    op.execute("""
        INSERT INTO schedules (id, user_id, title, description, start_at, end_at, kind)
        SELECT
            id,
            owner_id,
            title,
            NULLIF(description, ''),
            "limit"::timestamp AT TIME ZONE 'UTC',
            ("limit" + 1)::timestamp AT TIME ZONE 'UTC',
            'task'
        FROM legacy_tasks
    """)
    op.execute("""
        INSERT INTO tasks (schedule_id, due_date, done_flag)
        SELECT id, "limit"::timestamp AT TIME ZONE 'UTC', done_flag
        FROM legacy_tasks
    """)
    op.execute("""
        SELECT setval(
            pg_get_serial_sequence('schedules', 'id'),
            COALESCE((SELECT MAX(id) FROM schedules), 0) + 1,
            false
        )
    """)
    op.drop_table('legacy_tasks')


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table('legacy_tasks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('owner_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('description', sa.String(length=1000), nullable=False),
    sa.Column('limit', sa.Date(), nullable=False),
    sa.Column('done_flag', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # 旧tasksに戻せるのはkind=taskのScheduleだけで、それ以外のデータは失われる
    op.execute("""
        INSERT INTO legacy_tasks (id, owner_id, title, description, "limit", done_flag)
        SELECT
            s.id,
            s.user_id,
            s.title,
            LEFT(COALESCE(s.description, ''), 1000),
            (t.due_date AT TIME ZONE 'UTC')::date,
            t.done_flag
        FROM schedules s
        JOIN tasks t ON t.schedule_id = s.id
    """)

    op.drop_index(op.f('ix_transactions_occurred_at'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_account_id'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_user_id'), table_name='transactions')
    op.drop_table('transactions')
    op.drop_index(op.f('ix_planned_transactions_expected_date'), table_name='planned_transactions')
    op.drop_index(op.f('ix_planned_transactions_account_id'), table_name='planned_transactions')
    op.drop_index(op.f('ix_planned_transactions_schedule_id'), table_name='planned_transactions')
    op.drop_index(op.f('ix_planned_transactions_user_id'), table_name='planned_transactions')
    op.drop_table('planned_transactions')
    op.drop_index(op.f('ix_accounts_user_id'), table_name='accounts')
    op.drop_table('accounts')
    op.drop_table('shifts')
    op.drop_index(op.f('ix_tasks_due_date'), table_name='tasks')
    op.drop_table('tasks')
    op.drop_index(op.f('ix_schedules_start_at'), table_name='schedules')
    op.drop_index(op.f('ix_schedules_user_id'), table_name='schedules')
    op.drop_table('schedules')

    op.rename_table('legacy_tasks', 'tasks')
    # rename_tableでは主キーのシーケンス名が変わらないため、tasks_id_seqの名前に戻す
    op.execute("ALTER SEQUENCE legacy_tasks_id_seq RENAME TO tasks_id_seq")
    op.execute("ALTER INDEX legacy_tasks_pkey RENAME TO tasks_pkey")
    op.execute("""
        SELECT setval(
            pg_get_serial_sequence('tasks', 'id'),
            COALESCE((SELECT MAX(id) FROM tasks), 0) + 1,
            false
        )
    """)
    op.create_index(op.f('ix_tasks_title'), 'tasks', ['title'], unique=False)
