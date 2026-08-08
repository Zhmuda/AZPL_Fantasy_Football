"""add_system_settings

Revision ID: 2638208200e8
Revises: 067c8c25bdaf
Create Date: 2026-08-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2638208200e8'
down_revision: Union[str, None] = '067c8c25bdaf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('system_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('sofascore_provider', sa.String(length=20), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.execute(
        "INSERT INTO system_settings (id, sofascore_provider) VALUES (1, 'datafc')"
    )


def downgrade() -> None:
    op.drop_table('system_settings')
