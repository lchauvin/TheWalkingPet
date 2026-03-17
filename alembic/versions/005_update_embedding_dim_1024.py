"""Update embedding dimensions from 1536 to 1024 for DINOv2 ViT-L/14

Revision ID: 005
Revises: 004
Create Date: 2026-03-16
"""
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_pet_images_embedding")
    op.execute("DROP INDEX IF EXISTS ix_sightings_embedding")

    op.execute(
        "ALTER TABLE pet_images ALTER COLUMN embedding TYPE vector(1024) USING NULL"
    )
    op.execute(
        "ALTER TABLE sightings ALTER COLUMN embedding TYPE vector(1024) USING NULL"
    )
    op.execute(
        "ALTER TABLE pets ALTER COLUMN embedding TYPE vector(1024) USING NULL"
    )

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
        "ALTER TABLE pet_images ALTER COLUMN embedding TYPE vector(1536) USING NULL"
    )
    op.execute(
        "ALTER TABLE sightings ALTER COLUMN embedding TYPE vector(1536) USING NULL"
    )
    op.execute(
        "ALTER TABLE pets ALTER COLUMN embedding TYPE vector(1536) USING NULL"
    )

    op.execute(
        "CREATE INDEX ix_pet_images_embedding ON pet_images "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )
    op.execute(
        "CREATE INDEX ix_sightings_embedding ON sightings "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )
