"""merge heads

Revision ID: 5b0d36332452
Revises: c8d9e0f1a2b3, b9984ee269ee
Create Date: 2026-09-12 23:04:46.324626

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '5b0d36332452'
down_revision: Union[str, Sequence[str], None] = ('c8d9e0f1a2b3', 'b9984ee269ee')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    pass

def downgrade() -> None:
    """Downgrade schema."""
    pass
