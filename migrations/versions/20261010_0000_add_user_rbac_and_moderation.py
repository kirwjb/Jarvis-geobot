"""Add user RBAC role, is_muted, and created_at fields.

Revision ID: 20261010_rbac_audit
Revises: drop_groups_tables_20261007
Create Date: 2026-10-10 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '20261010_rbac_audit'
down_revision: Union[str, Sequence[str], None] = 'drop_groups_tables_20261007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('users', sa.Column('is_muted', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('users', sa.Column('role', sa.String(length=20), server_default='USER', nullable=False))
    op.add_column('users', sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False))
    op.execute("UPDATE users SET role = 'ADMIN' WHERE is_admin = true;")

def downgrade() -> None:
    op.drop_column('users', 'created_at')
    op.drop_column('users', 'role')
    op.drop_column('users', 'is_muted')
