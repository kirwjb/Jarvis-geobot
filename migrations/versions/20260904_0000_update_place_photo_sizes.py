"""update place photo sizes to thumb and medium webp

Revision ID: a1b2c3d4e5f7
Revises: 8f782bd85c59
Create Date: 2026-09-04 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f7'
down_revision = '8f782bd85c59'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('place_photos', sa.Column('local_url_thumb', sa.String(), nullable=True))
    op.add_column('place_photos', sa.Column('local_url_medium', sa.String(), nullable=True))

    op.drop_column('place_photos', 'local_url')

def downgrade() -> None:
    op.add_column('place_photos', sa.Column('local_url', sa.String(), nullable=True))
    op.drop_column('place_photos', 'local_url_medium')
    op.drop_column('place_photos', 'local_url_thumb')
