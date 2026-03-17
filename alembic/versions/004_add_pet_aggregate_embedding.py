"""Add aggregate embedding column to pets table

Revision ID: 004
Revises: 003
Create Date: 2026-03-16
"""
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE pets ADD COLUMN IF NOT EXISTS embedding vector(1536)")


def downgrade() -> None:
    op.drop_column("pets", "embedding")
