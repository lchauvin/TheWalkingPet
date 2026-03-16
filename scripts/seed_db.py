"""Seed the database with test data.

Usage:
    uv run python scripts/seed_db.py
"""
import asyncio
import uuid

from src.db.session import AsyncSessionLocal
from src.db.models import Pet, Species, User
from src.utils.security import hash_password


async def seed():
    async with AsyncSessionLocal() as db:
        # Create test user
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            hashed_password=hash_password("password123"),
            display_name="Test User",
        )
        db.add(user)

        # Create test pets
        cat = Pet(
            id=uuid.uuid4(),
            owner_id=user.id,
            name="Whiskers",
            species=Species.CAT,
            breed="Tabby",
            description="Orange tabby with white paws",
        )
        dog = Pet(
            id=uuid.uuid4(),
            owner_id=user.id,
            name="Buddy",
            species=Species.DOG,
            breed="Labrador",
            description="Yellow lab, very friendly",
        )
        db.add(cat)
        db.add(dog)

        await db.commit()
        print(f"Created user: {user.email} (id={user.id})")
        print(f"Created pet: {cat.name} (id={cat.id})")
        print(f"Created pet: {dog.name} (id={dog.id})")


if __name__ == "__main__":
    asyncio.run(seed())
