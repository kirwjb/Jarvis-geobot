"""add places table

Revision ID: add_places_table
Revises: 0a332c68f284
Create Date: 2026-09-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "add_places_table"

down_revision: Union[
    str,
    Sequence[str],
    None,
] = "8f782bd85c59"

branch_labels: Union[
    str,
    Sequence[str],
    None,
] = None

depends_on: Union[
    str,
    Sequence[str],
    None,
] = None

def upgrade() -> None:
    """Create places table."""

    op.create_table(
        "places",

        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),

        sa.Column(
            "place_id",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "name",
            sa.String(length=500),
            nullable=False,
        ),

        sa.Column(
            "city",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "region",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "address",
            sa.String(length=1000),
            nullable=False,
            server_default="",
        ),

        sa.Column(
            "category",
            sa.String(length=100),
            nullable=False,
            server_default="misc",
        ),

        sa.Column(
            "lat",
            sa.Float(),
            nullable=False,
        ),

        sa.Column(
            "lon",
            sa.Float(),
            nullable=False,
        ),

        sa.Column(
            "hours",
            sa.String(length=500),
            nullable=True,
        ),

        sa.Column(
            "phone",
            sa.String(length=100),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
        ),

        sa.PrimaryKeyConstraint(
            "id",
            name="pk_places",
        ),

        sa.UniqueConstraint(
            "place_id",
            name="uq_places_place_id",
        ),
    )

    op.create_index(
        "ix_places_city",
        "places",
        ["city"],
        unique=False,
    )

    op.create_index(
        "ix_places_region",
        "places",
        ["region"],
        unique=False,
    )

    op.create_index(
        "ix_places_category",
        "places",
        ["category"],
        unique=False,
    )

def downgrade() -> None:
    """Drop places table."""

    op.drop_index(
        "ix_places_category",
        table_name="places",
    )

    op.drop_index(
        "ix_places_region",
        table_name="places",
    )

    op.drop_index(
        "ix_places_city",
        table_name="places",
    )

    op.drop_table("places")
