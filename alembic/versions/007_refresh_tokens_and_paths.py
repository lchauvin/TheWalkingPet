"""Refresh-token store, relative image paths, aggregate embedding index.

Revision ID: 007
Revises: 006
Create Date: 2026-09-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Server-side refresh tokens (rotation + revocation) ---
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_user_active", "refresh_tokens", ["user_id", "revoked_at"])

    # --- Normalise image paths to storage-root-relative POSIX form ---
    # Rows written on Windows hold values like
    #   storage\\images\\pets\\<uuid>\\<file>.jpg
    # while the media route addresses them as pets/<uuid>/<file>.jpg.
    for table in ("pet_images", "sightings"):
        op.execute(
            f"""
            UPDATE {table}
            SET image_path = regexp_replace(
                replace(image_path, '\\', '/'),
                '^\\.?/?storage/images/?',
                ''
            )
            """
        )

    # The media route authorises a request by looking the stored path up.
    op.create_index("ix_pet_images_image_path", "pet_images", ["image_path"])
    op.create_index("ix_sightings_image_path", "sightings", ["image_path"])

    # --- Index the aggregate embedding, like its sibling columns ---
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pets_embedding ON pets "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_pets_embedding")
    op.drop_index("ix_sightings_image_path", table_name="sightings")
    op.drop_index("ix_pet_images_image_path", table_name="pet_images")
    # Path normalisation is not reversed: the relative form is a superset of the
    # information the absolute form carried.
    op.drop_index("ix_refresh_tokens_user_active", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
