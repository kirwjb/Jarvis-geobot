"""Add photo_reports table for moderation and reporting.

Revision ID: 20261022_photo_reports
Revises: 20261010_rbac_audit
Create Date: 2026-10-22 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '20261022_photo_reports'
down_revision: Union[str, Sequence[str], None] = '20261010_rbac_audit'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'photo_reports',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('place_id', sa.String(length=255), nullable=False),
        sa.Column('photo_url', sa.String(length=1000), nullable=True),
        sa.Column('reason', sa.String(length=500), nullable=False, server_default='inappropriate'),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_photo_reports_place_id'), 'photo_reports', ['place_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_photo_reports_place_id'), table_name='photo_reports')
    op.drop_table('photo_reports')
