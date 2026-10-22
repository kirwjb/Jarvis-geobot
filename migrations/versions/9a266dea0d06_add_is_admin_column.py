"""add is_admin column

Revision ID: 9a266dea0d06
Revises: d42a80604298
Create Date: 2026-07-06 19:09:35.417561

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '9a266dea0d06'
down_revision: Union[str, Sequence[str], None] = 'd42a80604298'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('favorites', sa.Column('place_id', sa.String(), nullable=True))
    op.execute("UPDATE favorites SET place_id = '' WHERE place_id IS NULL")  
    op.alter_column('favorites', 'place_id', nullable=False)

    op.alter_column('favorites', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False,
               existing_server_default=sa.text('now()'))
    op.create_index(op.f('ix_favorites_user_id'), 'favorites', ['user_id'], unique=False)

    op.alter_column('group_members', 'role',
               existing_type=sa.VARCHAR(),
               nullable=False,
               existing_server_default=sa.text("'member'::character varying"))

    op.execute("UPDATE group_members SET joined_at = NOW() WHERE joined_at IS NULL")
    op.alter_column('group_members', 'joined_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)

    op.alter_column('group_members', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False,
               existing_server_default=sa.text('CURRENT_TIMESTAMP'))

    op.alter_column('groups', 'is_voting_active',
               existing_type=sa.BOOLEAN(),
               nullable=False,
               existing_server_default=sa.text('false'))

    op.add_column('users', sa.Column('is_admin', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.create_index(op.f('ix_users_user_id'), 'users', ['user_id'], unique=False)

    op.create_index(op.f('ix_history_user_id'), 'history', ['user_id'], unique=False)

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_history_user_id'), table_name='history')
    op.drop_index(op.f('ix_users_user_id'), table_name='users')
    op.drop_column('users', 'is_admin')

    op.alter_column('groups', 'is_voting_active',
               existing_type=sa.BOOLEAN(),
               nullable=True,
               existing_server_default=sa.text('false'))
    op.alter_column('group_members', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True,
               existing_server_default=sa.text('CURRENT_TIMESTAMP'))
    op.alter_column('group_members', 'joined_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
    op.alter_column('group_members', 'role',
               existing_type=sa.VARCHAR(),
               nullable=True,
               existing_server_default=sa.text("'member'::character varying"))

    op.drop_index(op.f('ix_favorites_user_id'), table_name='favorites')
    op.alter_column('favorites', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True,
               existing_server_default=sa.text('now()'))
    op.drop_column('favorites', 'place_id')
