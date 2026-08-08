"""add_sync_logs

Revision ID: 9f1c4a7b2e3d
Revises: 2638208200e8
Create Date: 2026-08-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9f1c4a7b2e3d'
down_revision: Union[str, None] = '2638208200e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('sync_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('task_name', sa.String(length=100), nullable=False),
    sa.Column('target', sa.String(length=100), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('message', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sync_logs_status', 'sync_logs', ['status'])
    op.create_index('ix_sync_logs_task_name', 'sync_logs', ['task_name'])


def downgrade() -> None:
    op.drop_index('ix_sync_logs_task_name', table_name='sync_logs')
    op.drop_index('ix_sync_logs_status', table_name='sync_logs')
    op.drop_table('sync_logs')
