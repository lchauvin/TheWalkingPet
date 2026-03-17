"""Update embedding dimensions from 256 to 1536 for MegaDescriptor

Revision ID: 003
Revises: 002
Create Date: 2026-03-16
"""
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop existing IVFFlat indexes (required before changing column type)
    op.execute("DROP INDEX IF EXISTS ix_pet_images_embedding")
    op.execute("DROP INDEX IF EXISTS ix_sightings_embedding")

    # Alter column types to vector(1536)
    op.execute(
        "ALTER TABLE pet_images ALTER COLUMN embedding TYPE vector(1536) "
        "USING NULL"
    )
    op.execute(
        "ALTER TABLE sightings ALTER COLUMN embedding TYPE vector(1536) "
        "USING NULL"
    )

    # Recreate IVFFlat indexes for the new dimension
    op.execute(
        "CREATE INDEX ix_pet_images_embedding ON pet_images "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )
    op.execute(
        "CREATE INDEX ix_sightings_embedding ON sightings "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_pet_images_embedding")
    op.execute("DROP INDEX IF EXISTS ix_sightings_embedding")

    op.execute(
        "ALTER TABLE pet_images ALTER COLUMN embedding TYPE vector(256) "
        "USING NULL"
    )
    op.execute(
        "ALTER TABLE sightings ALTER COLUMN embedding TYPE vector(256) "
        "USING NULL"
    )

    op.execute(
        "CREATE INDEX ix_pet_images_embedding ON pet_images "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )
    op.execute(
        "CREATE INDEX ix_sightings_embedding ON sightings "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )
