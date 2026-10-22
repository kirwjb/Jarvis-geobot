"""Init database tables

Revision ID: d42a80604298
Revises: 
Create Date: 2026-06-30 18:53:38.954917

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'd42a80604298'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('favorites', sa.Column('id', sa.Integer(), autoincrement=True, nullable=False))
    op.add_column('favorites', sa.Column('place_name', sa.String(), nullable=False))
    op.add_column('favorites', sa.Column('lat', sa.Float(), nullable=False))
    op.add_column('favorites', sa.Column('lon', sa.Float(), nullable=False))
    op.create_foreign_key(None, 'favorites', 'users', ['user_id'], ['user_id'], ondelete='CASCADE')
    op.drop_column('favorites', 'attraction_name')
    op.drop_column('favorites', 'added_at')
    op.drop_column('favorites', 'city')
    op.add_column('history', sa.Column('query', sa.String(), nullable=True))
    op.execute("UPDATE history SET query = 'Старый запрос' WHERE query IS NULL")
    op.alter_column('history', 'query', nullable=False)
    op.alter_column('history', 'user_id',
               existing_type=sa.BIGINT(),
               nullable=False)
    op.alter_column('history', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False,
               existing_server_default=sa.text('CURRENT_TIMESTAMP'))
    op.create_foreign_key(None, 'history', 'users', ['user_id'], ['user_id'], ondelete='CASCADE')
    op.drop_column('history', 'city')
    op.drop_column('history', 'route')
    op.drop_column('history', 'attractions')
    op.alter_column('osm_cache', 'city',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               nullable=False)
    op.alter_column('osm_cache', 'name',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               nullable=False)
    op.alter_column('osm_cache', 'address',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('osm_cache', 'lat',
               existing_type=sa.REAL(),
               type_=sa.Float(),
               nullable=False)
    op.alter_column('osm_cache', 'lon',
               existing_type=sa.REAL(),
               type_=sa.Float(),
               nullable=False)
    op.alter_column('osm_cache', 'rating',
               existing_type=sa.REAL(),
               type_=sa.Float(),
               nullable=False)
    op.alter_column('osm_cache', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False,
               existing_server_default=sa.text('CURRENT_TIMESTAMP'))
    op.create_index(op.f('ix_osm_cache_city'), 'osm_cache', ['city'], unique=False)
    op.drop_column('osm_cache', 'image_url')
    op.drop_column('osm_cache', 'type')
    op.drop_column('osm_cache', 'phone')
    op.drop_column('osm_cache', 'hours')
    op.alter_column('users', 'username',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('users', 'tokens',
               existing_type=sa.INTEGER(),
               nullable=False,
               existing_server_default=sa.text('5'))
    op.alter_column('users', 'last_reset',
               existing_type=sa.DATE(),
               nullable=False)
    op.add_column('viewed', sa.Column('id', sa.Integer(), autoincrement=True, nullable=False))
    op.add_column('viewed', sa.Column('place_name', sa.String(), nullable=False))
    op.alter_column('viewed', 'viewed_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False,
               existing_server_default=sa.text('CURRENT_TIMESTAMP'))
    op.create_foreign_key(None, 'viewed', 'users', ['user_id'], ['user_id'], ondelete='CASCADE')
    op.drop_column('viewed', 'attraction_name')
    op.drop_column('viewed', 'city')

def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('viewed', sa.Column('city', sa.TEXT(), autoincrement=False, nullable=False))
    op.add_column('viewed', sa.Column('attraction_name', sa.TEXT(), autoincrement=False, nullable=False))
    op.drop_constraint(None, 'viewed', type_='foreignkey')
    op.alter_column('viewed', 'viewed_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True,
               existing_server_default=sa.text('CURRENT_TIMESTAMP'))
    op.drop_column('viewed', 'place_name')
    op.drop_column('viewed', 'id')
    op.alter_column('users', 'last_reset',
               existing_type=sa.DATE(),
               nullable=True)
    op.alter_column('users', 'tokens',
               existing_type=sa.INTEGER(),
               nullable=True,
               existing_server_default=sa.text('5'))
    op.alter_column('users', 'username',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.add_column('osm_cache', sa.Column('hours', sa.TEXT(), autoincrement=False, nullable=True))
    op.add_column('osm_cache', sa.Column('phone', sa.TEXT(), autoincrement=False, nullable=True))
    op.add_column('osm_cache', sa.Column('type', sa.TEXT(), autoincrement=False, nullable=True))
    op.add_column('osm_cache', sa.Column('image_url', sa.TEXT(), autoincrement=False, nullable=True))
    op.drop_index(op.f('ix_osm_cache_city'), table_name='osm_cache')
    op.alter_column('osm_cache', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True,
               existing_server_default=sa.text('CURRENT_TIMESTAMP'))
    op.alter_column('osm_cache', 'rating',
               existing_type=sa.Float(),
               type_=sa.REAL(),
               nullable=True)
    op.alter_column('osm_cache', 'lon',
               existing_type=sa.Float(),
               type_=sa.REAL(),
               nullable=True)
    op.alter_column('osm_cache', 'lat',
               existing_type=sa.Float(),
               type_=sa.REAL(),
               nullable=True)
    op.alter_column('osm_cache', 'address',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('osm_cache', 'name',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               nullable=True)
    op.alter_column('osm_cache', 'city',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               nullable=True)
    op.add_column('history', sa.Column('attractions', sa.TEXT(), autoincrement=False, nullable=True))
    op.add_column('history', sa.Column('route', sa.TEXT(), autoincrement=False, nullable=True))
    op.add_column('history', sa.Column('city', sa.TEXT(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'history', type_='foreignkey')
    op.alter_column('history', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True,
               existing_server_default=sa.text('CURRENT_TIMESTAMP'))
    op.alter_column('history', 'user_id',
               existing_type=sa.BIGINT(),
               nullable=True)
    op.drop_column('history', 'query')
    op.add_column('favorites', sa.Column('city', sa.TEXT(), autoincrement=False, nullable=False))
    op.add_column('favorites', sa.Column('added_at', postgresql.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), autoincrement=False, nullable=True))
    op.add_column('favorites', sa.Column('attraction_name', sa.TEXT(), autoincrement=False, nullable=False))
    op.drop_constraint(None, 'favorites', type_='foreignkey')
    op.drop_column('favorites', 'lon')
    op.drop_column('favorites', 'lat')
    op.drop_column('favorites', 'place_name')
    op.drop_column('favorites', 'id')
