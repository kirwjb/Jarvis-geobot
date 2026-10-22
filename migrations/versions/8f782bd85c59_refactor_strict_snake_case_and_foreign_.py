"""refactor: strict snake_case and foreign keys cascade

Revision ID: 8f782bd85c59
Revises: 0a332c68f284
Create Date: 2026-07-10 12:50:14.785241

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '8f782bd85c59'
down_revision: Union[str, Sequence[str], None] = '0a332c68f284'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    op.execute("UPDATE favorites SET address = 'Неизвестно' WHERE address IS NULL")
    op.drop_table('viewed')
    op.alter_column('favorites', 'address',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               nullable=False)
    op.drop_column('favorites', 'name')
    op.drop_constraint(op.f('uqGroupMember'), 'group_members', type_='unique')
    op.create_unique_constraint('uq_group_member', 'group_members', ['group_id', 'user_id'])
    op.create_foreign_key(None, 'group_members', 'groups', ['group_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'group_members', 'users', ['user_id'], ['user_id'], ondelete='CASCADE')
    op.drop_column('group_members', 'created_at')
    op.drop_constraint(op.f('uqGroupVote'), 'group_votes', type_='unique')
    op.create_unique_constraint('uq_group_vote', 'group_votes', ['group_id', 'user_id', 'place_id'])
    op.create_foreign_key(None, 'group_votes', 'users', ['user_id'], ['user_id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'group_votes', 'groups', ['group_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'groups', 'users', ['owner_id'], ['user_id'], ondelete='CASCADE')
    op.drop_column('osm_cache', 'created_at')
    op.drop_column('osm_cache', 'rating')

def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('osm_cache', sa.Column('rating', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False))
    op.add_column('osm_cache', sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), autoincrement=False, nullable=False))
    op.drop_constraint(None, 'groups', type_='foreignkey')
    op.drop_constraint(None, 'group_votes', type_='foreignkey')
    op.drop_constraint(None, 'group_votes', type_='foreignkey')
    op.drop_constraint('uq_group_vote', 'group_votes', type_='unique')
    op.create_unique_constraint(op.f('uqGroupVote'), 'group_votes', ['group_id', 'user_id', 'place_id'], postgresql_nulls_not_distinct=False)
    op.add_column('group_members', sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), autoincrement=False, nullable=False))
    op.drop_constraint(None, 'group_members', type_='foreignkey')
    op.drop_constraint(None, 'group_members', type_='foreignkey')
    op.drop_constraint('uq_group_member', 'group_members', type_='unique')
    op.create_unique_constraint(op.f('uqGroupMember'), 'group_members', ['group_id', 'user_id'], postgresql_nulls_not_distinct=False)
    op.add_column('favorites', sa.Column('name', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    op.alter_column('favorites', 'address',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               nullable=True)
    op.create_table('viewed',
    sa.Column('user_id', sa.BIGINT(), autoincrement=False, nullable=False),
    sa.Column('viewed_at', postgresql.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), autoincrement=False, nullable=False),
    sa.Column('id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('place_name', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], name=op.f('viewed_user_id_fkey'), ondelete='CASCADE')
    )
