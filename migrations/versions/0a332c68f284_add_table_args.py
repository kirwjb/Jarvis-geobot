"""add table_args

Revision ID: 0a332c68f284
Revises: 9a266dea0d06
Create Date: 2026-07-07 12:50:16.396593

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0a332c68f284'
down_revision: Union[str, Sequence[str], None] = '9a266dea0d06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint('uqGroupMember', 'group_members', ['group_id', 'user_id'])
    op.create_unique_constraint('uqGroupVote', 'group_votes', ['group_id', 'user_id', 'place_id'])

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uqGroupVote', 'group_votes', type_='unique')
    op.drop_constraint('uqGroupMember', 'group_members', type_='unique')
