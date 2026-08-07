import asyncio
from app.core.database import AsyncSessionLocal


async def seed_data():
    """Initial database seed script."""
    async with AsyncSessionLocal() as session:
        print("Seeding data...")
        # Add seed logic here as models are defined
        print("Seeding completed successfully.")


if __name__ == "__main__":
    asyncio.run(seed_data())
