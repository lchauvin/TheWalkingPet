"""Record where a sighting's coordinates came from, and when the photo was taken.

Revision ID: 008
Revises: 007
Create Date: 2026-09-09
"""
from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


_LOCATION_SOURCE = sa.Enum("DEVICE", "EXIF", name="locationsource")


def upgrade() -> None:
    bind = op.get_bind()
    _LOCATION_SOURCE.create(bind, checkfirst=True)

    # Every row predating this migration was filed from the reporter's device
    # GPS, so DEVICE is an accurate backfill rather than a placeholder. Added
    # with a server default so the backfill needs no separate UPDATE, then
    # dropped: the application supplies the value from here on.
    op.add_column(
        "sightings",
        sa.Column(
            "location_source",
            _LOCATION_SOURCE,
            nullable=False,
            server_default="DEVICE",
        ),
    )
    op.alter_column("sightings", "location_source", server_default=None)

    op.add_column(
        "sightings",
        sa.Column("taken_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sightings", "taken_at")
    op.drop_column("sightings", "location_source")
    _LOCATION_SOURCE.drop(op.get_bind(), checkfirst=True)
