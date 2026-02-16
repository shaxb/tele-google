"""Baseline: mark current schema as migration starting point

This migration represents the existing production schema as of 2026-02-16.
It does NOT create or alter any tables — the schema already exists.

To bootstrap a new database from scratch, run: alembic upgrade head

Revision ID: 0001_baseline
Revises: (none)
Create Date: 2026-02-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Nothing to do — schema already exists in production."""
    pass


def downgrade() -> None:
    """Dropping all tables is irreversible in a baseline migration."""
    raise RuntimeError("Cannot downgrade past the baseline migration.")
