import uuid
from datetime import datetime
from enum import Enum as PyEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    Enum,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Species(str, PyEnum):
    CAT = "CAT"
    DOG = "DOG"
    OTHER = "OTHER"


class LostStatus(str, PyEnum):
    ACTIVE = "ACTIVE"
    FOUND = "FOUND"
    CANCELLED = "CANCELLED"


class MatchStatus(str, PyEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    notify_lost_pets: Mapped[bool] = mapped_column(Boolean, default=True)
    notification_radius_km: Mapped[float] = mapped_column(Float, default=5.0)
    fcm_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pets: Mapped[list["Pet"]] = relationship("Pet", back_populates="owner", cascade="all, delete-orphan")
    sightings: Mapped[list["Sighting"]] = relationship("Sighting", back_populates="reporter")


class Pet(Base):
    __tablename__ = "pets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    species: Mapped[Species] = mapped_column(Enum(Species), nullable=False)
    breed: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_microchipped: Mapped[bool] = mapped_column(Boolean, default=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped["User"] = relationship("User", back_populates="pets")
    images: Mapped[list["PetImage"]] = relationship("PetImage", back_populates="pet", cascade="all, delete-orphan")
    lost_declarations: Mapped[list["LostDeclaration"]] = relationship("LostDeclaration", back_populates="pet", passive_deletes=True)

    __table_args__ = (
        Index("ix_pets_lat_lon", "latitude", "longitude"),
    )


class PetImage(Base):
    __tablename__ = "pet_images"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pets.id", ondelete="CASCADE"), nullable=False)
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(256), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pet: Mapped["Pet"] = relationship("Pet", back_populates="images")


class LostDeclaration(Base):
    __tablename__ = "lost_declarations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pets.id", ondelete="CASCADE"), nullable=False)
    last_seen_lat: Mapped[float] = mapped_column(Float, nullable=False)
    last_seen_lon: Mapped[float] = mapped_column(Float, nullable=False)
    search_radius_km: Mapped[float] = mapped_column(Float, default=0.5)
    reward_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[LostStatus] = mapped_column(Enum(LostStatus), default=LostStatus.ACTIVE)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    pet: Mapped["Pet"] = relationship("Pet", back_populates="lost_declarations")
    matches: Mapped[list["Match"]] = relationship("Match", back_populates="lost_declaration")

    __table_args__ = (
        Index("ix_lost_lat_lon", "last_seen_lat", "last_seen_lon"),
    )


class Sighting(Base):
    __tablename__ = "sightings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reporter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(256), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    species_detected: Mapped[Species | None] = mapped_column(Enum(Species), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    reporter: Mapped["User | None"] = relationship("User", back_populates="sightings")
    matches: Mapped[list["Match"]] = relationship("Match", back_populates="sighting")

    __table_args__ = (
        Index("ix_sightings_lat_lon", "latitude", "longitude"),
    )


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sighting_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sightings.id", ondelete="CASCADE"), nullable=False)
    lost_declaration_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("lost_declarations.id", ondelete="CASCADE"), nullable=False)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[MatchStatus] = mapped_column(Enum(MatchStatus), default=MatchStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    sighting: Mapped["Sighting"] = relationship("Sighting", back_populates="matches")
    lost_declaration: Mapped["LostDeclaration"] = relationship("LostDeclaration", back_populates="matches")
