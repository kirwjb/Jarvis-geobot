"""add trip_start, group_proposals, and group_messages

Revision ID: c8d9e0f1a2b3
Revises: a1b2c3d4e5f7
Create Date: 2026-09-12 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'c8d9e0f1a2b3'
down_revision = 'a1b2c3d4e5f7'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('groups', sa.Column('trip_start', sa.Date(), nullable=True))
    op.create_index('ix_groups_trip_start', 'groups', ['trip_start'], unique=False)

    op.create_table(
        'group_proposals',
        sa.Column('id', sa.Integer(), sa.Identity(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.BigInteger(), nullable=False),
        sa.Column('place_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('group_id', 'place_id', name='uq_group_proposals_group_place')
    )
    op.create_index('ix_group_proposals_group_id', 'group_proposals', ['group_id'], unique=False)

    op.create_table(
        'group_messages',
        sa.Column('id', sa.Integer(), sa.Identity(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.BigInteger(), nullable=False),
        sa.Column('text', sa.String(length=2000), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_group_messages_group_id', 'group_messages', ['group_id'], unique=False)

def downgrade() -> None:
    op.drop_index('ix_group_messages_group_id', table_name='group_messages')
    op.drop_table('group_messages')

    op.drop_index('ix_group_proposals_group_id', table_name='group_proposals')
    op.drop_table('group_proposals')

    op.drop_index('ix_groups_trip_start', table_name='groups')
    op.drop_column('groups', 'trip_start')
