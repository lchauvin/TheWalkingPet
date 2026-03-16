"""Add fcm_token to users

Revision ID: 002
Revises: 001
Create Date: 2026-03-16
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("fcm_token", sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "fcm_token")
