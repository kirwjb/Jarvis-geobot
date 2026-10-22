"""Drop groups tables across the entire database.

Revision ID: drop_groups_tables_20261007
Revises: 5b0d36332452
Create Date: 2026-10-07 21:33:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'drop_groups_tables_20261007'
down_revision: Union[str, Sequence[str], None] = '5b0d36332452'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Drop groups, group_members, group_votes, group_proposals, group_messages."""
    op.execute("DROP TABLE IF EXISTS group_messages CASCADE;")
    op.execute("DROP TABLE IF EXISTS group_proposals CASCADE;")
    op.execute("DROP TABLE IF EXISTS group_votes CASCADE;")
    op.execute("DROP TABLE IF EXISTS group_members CASCADE;")
    op.execute("DROP TABLE IF EXISTS groups CASCADE;")

def downgrade() -> None:
    """Recreate basic groups tables on downgrade if necessary."""
    op.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            id SERIAL PRIMARY KEY,
            name VARCHAR NOT NULL,
            owner_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            is_voting_active BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS group_members (
            id SERIAL PRIMARY KEY,
            group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
            user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            role VARCHAR(20) DEFAULT 'member',
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_group_member UNIQUE(group_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS group_votes (
            id SERIAL PRIMARY KEY,
            group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
            user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            place_id VARCHAR NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_group_vote UNIQUE(group_id, user_id, place_id)
        );
    """)
