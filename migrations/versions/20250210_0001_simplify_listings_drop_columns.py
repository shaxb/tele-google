"""Simplify listings - drop extracted attribute columns

Drop columns that are no longer needed after removing Meilisearch
and complex attribute extraction. Only raw_text + embedding remain.

Revision ID: simplify001
Revises: d62557355ac3
Create Date: 2025-02-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'simplify001'
down_revision: Union[str, None] = 'd62557355ac3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop columns no longer needed
    op.drop_column('listings', 'attributes')
    op.drop_column('listings', 'price_min')
    op.drop_column('listings', 'price_max')
    op.drop_column('listings', 'currency')
    op.drop_column('listings', 'location')
    op.drop_column('listings', 'phone_numbers')
    op.drop_column('listings', 'language')
    op.drop_column('listings', 'category_guess')
    
    # Drop indexes on removed columns
    op.drop_index('ix_listings_price_min', table_name='listings', if_exists=True)
    op.drop_index('ix_listings_location', table_name='listings', if_exists=True)
    op.drop_index('ix_listings_category_guess', table_name='listings', if_exists=True)


def downgrade() -> None:
    # Re-add columns if rolling back
    op.add_column('listings', sa.Column('attributes', postgresql.JSONB(), nullable=True, server_default='{}'))
    op.add_column('listings', sa.Column('price_min', sa.Numeric(), nullable=True))
    op.add_column('listings', sa.Column('price_max', sa.Numeric(), nullable=True))
    op.add_column('listings', sa.Column('currency', sa.String(10), nullable=True))
    op.add_column('listings', sa.Column('location', sa.Text(), nullable=True))
    op.add_column('listings', sa.Column('phone_numbers', postgresql.ARRAY(sa.Text()), nullable=True))
    op.add_column('listings', sa.Column('language', sa.String(10), nullable=True))
    op.add_column('listings', sa.Column('category_guess', sa.Text(), nullable=True))
    
    # Re-create indexes
    op.create_index('ix_listings_price_min', 'listings', ['price_min'])
    op.create_index('ix_listings_location', 'listings', ['location'])
    op.create_index('ix_listings_category_guess', 'listings', ['category_guess'])
