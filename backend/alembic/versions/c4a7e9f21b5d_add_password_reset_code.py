"""add_password_reset_code

Revision ID: c4a7e9f21b5d
Revises: b3d8f61a9c7e
Create Date: 2026-08-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4a7e9f21b5d'
down_revision: Union[str, None] = 'b3d8f61a9c7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('reset_code', sa.String(length=8), nullable=True))
    op.add_column('users', sa.Column('reset_code_expires', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'reset_code_expires')
    op.drop_column('users', 'reset_code')
