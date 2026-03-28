"""Add unique constraint to prevent duplicate match pairs.

Revision ID: 006
Revises: 005
Create Date: 2026-03-27
"""
from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Keep only the newest row for duplicate (sighting_id, lost_declaration_id) pairs.
    op.execute(
        """
        DELETE FROM matches m
        USING matches dup
        WHERE m.sighting_id = dup.sighting_id
          AND m.lost_declaration_id = dup.lost_declaration_id
          AND (m.created_at, m.id) < (dup.created_at, dup.id)
        """
    )
    op.create_unique_constraint(
        "uq_matches_sighting_lost",
        "matches",
        ["sighting_id", "lost_declaration_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_matches_sighting_lost", "matches", type_="unique")
