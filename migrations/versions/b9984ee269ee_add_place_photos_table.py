"""add place photos table

Revision ID: b9984ee269ee
Revises: add_places_table
Create Date: 2026-09-02 19:10:49.488949

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b9984ee269ee'
down_revision: Union[str, Sequence[str], None] = 'add_places_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "place_photos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("place_id", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("original_url", sa.Text(), nullable=False),
        sa.Column("local_url", sa.Text(), nullable=False),
        sa.Column("author", sa.Text(), nullable=True),
        sa.Column("license", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_place_photos_place_id"),
        "place_photos",
        ["place_id"],
        unique=False,
    )

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_place_photos_place_id"),
        table_name="place_photos",
    )
    op.drop_table("place_photos")
