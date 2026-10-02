"""migrate users to auth0

Revision ID: 8f3c2a1d9b7e
Revises: 236d16b6ca2d
Create Date: 2026-10-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f3c2a1d9b7e'
down_revision: Union[str, Sequence[str], None] = '236d16b6ca2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('auth_subject', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column(
        'created_at',
        sa.DateTime(timezone=True),
        server_default=sa.text('now()'),
        nullable=False
    ))
    # 既存ユーザーにはAuth0のsubが無いため、ログインできない仮の値を入れてからNOT NULLにする
    op.execute("UPDATE users SET auth_subject = 'legacy|' || id WHERE auth_subject IS NULL")
    op.alter_column('users', 'auth_subject', nullable=False)
    op.create_index(op.f('ix_users_auth_subject'), 'users', ['auth_subject'], unique=True)

    op.alter_column('users', 'email', existing_type=sa.String(), nullable=True)
    op.drop_column('users', 'hashed_password')
    op.drop_column('users', 'disabled')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('users', sa.Column('disabled', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column('users', sa.Column('hashed_password', sa.String(), server_default='', nullable=False))
    op.alter_column('users', 'disabled', server_default=None)
    op.alter_column('users', 'hashed_password', server_default=None)

    # emailがNULLのユーザーはNOT NULLに戻せないため、仮のメールアドレスを入れる
    op.execute("UPDATE users SET email = auth_subject || '@invalid.example' WHERE email IS NULL")
    op.alter_column('users', 'email', existing_type=sa.String(), nullable=False)

    op.drop_index(op.f('ix_users_auth_subject'), table_name='users')
    op.drop_column('users', 'created_at')
    op.drop_column('users', 'auth_subject')
