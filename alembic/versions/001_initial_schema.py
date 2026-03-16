"""Initial schema with pgvector

Revision ID: 001
Revises:
Create Date: 2026-03-14
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("google_id", sa.String(255), nullable=True),
        sa.Column("display_name", sa.String(100), nullable=True),
        sa.Column("latitude", sa.Float, nullable=True),
        sa.Column("longitude", sa.Float, nullable=True),
        sa.Column("notify_lost_pets", sa.Boolean, default=True),
        sa.Column("notification_radius_km", sa.Float, default=5.0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_google_id", "users", ["google_id"], unique=True)

    op.create_table(
        "pets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("species", sa.Enum("CAT", "DOG", "OTHER", name="species"), nullable=False),
        sa.Column("breed", sa.String(100), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_microchipped", sa.Boolean, default=False),
        sa.Column("latitude", sa.Float, nullable=True),
        sa.Column("longitude", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_pets_lat_lon", "pets", ["latitude", "longitude"])

    op.create_table(
        "pet_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("pet_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("image_path", sa.String(500), nullable=False),
        sa.Column("embedding", Vector(256), nullable=True),
        sa.Column("is_primary", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute(
        "CREATE INDEX ix_pet_images_embedding ON pet_images USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    op.create_table(
        "lost_declarations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("pet_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("last_seen_lat", sa.Float, nullable=False),
        sa.Column("last_seen_lon", sa.Float, nullable=False),
        sa.Column("search_radius_km", sa.Float, default=0.5),
        sa.Column("reward_amount", sa.Float, nullable=True),
        sa.Column("status", sa.Enum("ACTIVE", "FOUND", "CANCELLED", name="loststatus"), nullable=False, server_default="ACTIVE"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_lost_lat_lon", "lost_declarations", ["last_seen_lat", "last_seen_lon"])

    op.create_table(
        "sightings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("reporter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("image_path", sa.String(500), nullable=False),
        sa.Column("embedding", Vector(256), nullable=True),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("species_detected", sa.Enum("CAT", "DOG", "OTHER", name="species"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sightings_lat_lon", "sightings", ["latitude", "longitude"])
    op.execute(
        "CREATE INDEX ix_sightings_embedding ON sightings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    op.create_table(
        "matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sighting_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sightings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lost_declaration_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lost_declarations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("similarity_score", sa.Float, nullable=False),
        sa.Column("status", sa.Enum("PENDING", "CONFIRMED", "REJECTED", name="matchstatus"), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("matches")
    op.drop_table("sightings")
    op.drop_table("lost_declarations")
    op.drop_table("pet_images")
    op.drop_table("pets")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS matchstatus")
    op.execute("DROP TYPE IF EXISTS loststatus")
    op.execute("DROP TYPE IF EXISTS species")
