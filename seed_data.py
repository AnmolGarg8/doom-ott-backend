import asyncio
import uuid
from datetime import date
from sqlalchemy import select
from app.core.database import AsyncSessionLocal, Base, engine
from app.models.enums import AuthProvider, ContentStatus, ContentType, CouponDiscountType, SubscriptionStatus, TransactionStatus
from app.models.user import User, Profile, Role, AdminUser
from app.models.content import Category, Content, Episode, VideoAsset
from app.models.billing import SubscriptionPlan, Coupon


CATEGORIES_DATA = [
    {"name": "Action", "slug": "action"},
    {"name": "Sci-Fi", "slug": "sci-fi"},
    {"name": "Drama", "slug": "drama"},
    {"name": "Animation", "slug": "animation"},
    {"name": "Comedy", "slug": "comedy"},
    {"name": "Thriller", "slug": "thriller"},
    {"name": "Fantasy", "slug": "fantasy"},
    {"name": "Romance", "slug": "romance"},
]

PLANS_DATA = [
    {
        "name": "Mobile",
        "price": 4.99,
        "duration_days": 30,
        "features": ["1 Mobile Device", "480p SD Quality", "Ad-supported catalog"],
        "is_active": True,
    },
    {
        "name": "Standard",
        "price": 9.99,
        "duration_days": 30,
        "features": ["2 Screens HD", "1080p Full HD", "Unlimited Movies & Shows", "Download on 2 devices"],
        "is_active": True,
    },
    {
        "name": "Premium Ultra 4K",
        "price": 14.99,
        "duration_days": 30,
        "features": ["4 Screens Simultaneous", "4K Ultra HD + HDR", "Dolby Atmos Audio", "Unlimited Downloads"],
        "is_active": True,
    },
]

DEMO_CONTENT = [
    {
        "title": "Doom: The Beginning",
        "type": ContentType.MOVIE,
        "synopsis": "In a post-apocalyptic dystopia, a lone warrior emerges from the shadows to reclaim humanity's lost glory against rogue AI cyber-demons.",
        "cast": ["Karl Urban", "Dwayne Johnson", "Rosamund Pike"],
        "genre": ["Action", "Sci-Fi", "Thriller"],
        "language": "English",
        "content_rating": "R",
        "release_year": 2024,
        "duration_minutes": 135,
        "poster_url": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=600&auto=format&fit=crop",
        "backdrop_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=1200&auto=format&fit=crop",
        "status": ContentStatus.PUBLISHED,
    },
    {
        "title": "Tears of Steel",
        "type": ContentType.MOVIE,
        "synopsis": "Set in a dystopian future Amsterdam, a group of soldiers and scientists attempt to save the earth from a horde of destructive robots.",
        "cast": ["Derek de Lint", "Sergio Hasselbaink", "Rogier Schippers"],
        "genre": ["Sci-Fi", "Drama", "Action"],
        "language": "English",
        "content_rating": "PG-13",
        "release_year": 2023,
        "duration_minutes": 112,
        "poster_url": "https://images.unsplash.com/photo-1578632767115-351597cf2477?w=600&auto=format&fit=crop",
        "backdrop_url": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200&auto=format&fit=crop",
        "status": ContentStatus.PUBLISHED,
    },
    {
        "title": "Sintel: The Quest",
        "type": ContentType.MOVIE,
        "synopsis": "A lonely young woman searches the globe for her stolen dragon companion, discovering strength and heartbreak along the journey.",
        "cast": ["Halina Reijn", "Thom Hoffman"],
        "genre": ["Animation", "Fantasy", "Drama"],
        "language": "English",
        "content_rating": "PG",
        "release_year": 2022,
        "duration_minutes": 95,
        "poster_url": "https://images.unsplash.com/photo-1563089145-599997674d42?w=600&auto=format&fit=crop",
        "backdrop_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=1200&auto=format&fit=crop",
        "status": ContentStatus.PUBLISHED,
    },
    {
        "title": "Cyberpunk 2099",
        "type": ContentType.SERIES,
        "synopsis": "High-tech low-lifes clash in the neon-drenched metropolis of Neo-Veridia as corporate syndicates vie for human consciousness singularity.",
        "cast": ["Keanu Reeves", "Ana de Armas", "Idris Elba"],
        "genre": ["Sci-Fi", "Thriller", "Action"],
        "language": "English",
        "content_rating": "TV-MA",
        "release_year": 2025,
        "duration_minutes": None,
        "poster_url": "https://images.unsplash.com/photo-1542751371-adc38448a05e?w=600&auto=format&fit=crop",
        "backdrop_url": "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=1200&auto=format&fit=crop",
        "status": ContentStatus.PUBLISHED,
        "episodes": [
            {"season": 1, "episode_no": 1, "title": "Neon Awakening", "duration_minutes": 48},
            {"season": 1, "episode_no": 2, "title": "Silicon Protocol", "duration_minutes": 52},
            {"season": 1, "episode_no": 3, "title": "Ghost in the Lattice", "duration_minutes": 45},
            {"season": 1, "episode_no": 4, "title": "Singularity Vector", "duration_minutes": 55},
        ],
    },
    {
        "title": "Short Stories: Cosmos",
        "type": ContentType.SHORT,
        "synopsis": "A mind-bending anthology short exploring the beauty and vast mysteries of deep space interdimensional travel.",
        "cast": ["Narrator Alpha"],
        "genre": ["Sci-Fi", "Animation"],
        "language": "English",
        "content_rating": "G",
        "release_year": 2024,
        "duration_minutes": 18,
        "poster_url": "https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?w=600&auto=format&fit=crop",
        "backdrop_url": "https://images.unsplash.com/photo-1506703719100-a0f3a48c0f86?w=1200&auto=format&fit=crop",
        "status": ContentStatus.PUBLISHED,
    },
    {
        "title": "Elephants Dream",
        "type": ContentType.MOVIE,
        "synopsis": "Two strange visionaries explore a surreal machine realm governed by mechanical logic and hidden human desires.",
        "cast": ["Tygo Gernandt", "Cas Jansen"],
        "genre": ["Animation", "Sci-Fi"],
        "language": "English",
        "content_rating": "PG",
        "release_year": 2021,
        "duration_minutes": 88,
        "poster_url": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=600&auto=format&fit=crop",
        "backdrop_url": "https://images.unsplash.com/photo-1550684848-fac1c5b4e853?w=1200&auto=format&fit=crop",
        "status": ContentStatus.PUBLISHED,
    },
    {
        "title": "Caminandes: Llama Drama",
        "type": ContentType.SHORT,
        "synopsis": "Koro the comical llama encounters an impenetrable fence while trying to cross a desolate Patagonia road.",
        "cast": ["Animated Llama"],
        "genre": ["Animation", "Comedy"],
        "language": "English",
        "content_rating": "G",
        "release_year": 2023,
        "duration_minutes": 7,
        "poster_url": "https://images.unsplash.com/photo-1534188753412-3e26d0d618d6?w=600&auto=format&fit=crop",
        "backdrop_url": "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=1200&auto=format&fit=crop",
        "status": ContentStatus.PUBLISHED,
    },
    {
        "title": "Big Buck Bunny",
        "type": ContentType.MOVIE,
        "synopsis": "A large and lovable rabbit retaliates when bullying forest rodents ruin his peaceful morning routine.",
        "cast": ["Bunny", "Frank", "Rinky"],
        "genre": ["Animation", "Comedy"],
        "language": "English",
        "content_rating": "G",
        "release_year": 2022,
        "duration_minutes": 75,
        "poster_url": "https://images.unsplash.com/photo-1551024709-8f23befc6f87?w=600&auto=format&fit=crop",
        "backdrop_url": "https://images.unsplash.com/photo-1472214103451-9374bd1c798e?w=1200&auto=format&fit=crop",
        "status": ContentStatus.PUBLISHED,
    },
    {
        "title": "The Dark Horizon",
        "type": ContentType.SERIES,
        "synopsis": "When a deep space listening station receives an ominous signal from an uncharted galaxy, humanity's leaders face an existential dilemma.",
        "cast": ["Gillian Anderson", "David Strathairn"],
        "genre": ["Drama", "Thriller", "Sci-Fi"],
        "language": "English",
        "content_rating": "TV-14",
        "release_year": 2024,
        "duration_minutes": None,
        "poster_url": "https://images.unsplash.com/photo-1447433589675-4aaa569f3e05?w=600&auto=format&fit=crop",
        "backdrop_url": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200&auto=format&fit=crop",
        "status": ContentStatus.PUBLISHED,
        "episodes": [
            {"season": 1, "episode_no": 1, "title": "The Carrier Wave", "duration_minutes": 50},
            {"season": 1, "episode_no": 2, "title": "Red Shift Echo", "duration_minutes": 47},
        ],
    },
    {
        "title": "Cosmic Odyssey",
        "type": ContentType.MOVIE,
        "synopsis": "An epic journey through wormholes and alien stellar systems in search of a new home for civilization.",
        "cast": ["Matthew McConaughey", "Jessica Chastain"],
        "genre": ["Sci-Fi", "Action", "Drama"],
        "language": "English",
        "content_rating": "PG-13",
        "release_year": 2025,
        "duration_minutes": 142,
        "poster_url": "https://images.unsplash.com/photo-1506703719100-a0f3a48c0f86?w=600&auto=format&fit=crop",
        "backdrop_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=1200&auto=format&fit=crop",
        "status": ContentStatus.PUBLISHED,
    },
]


async def seed_data():
    print("Starting database seeding...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Seed Categories
        for cat in CATEGORIES_DATA:
            res = await session.execute(select(Category).where(Category.slug == cat["slug"]))
            if not res.scalars().first():
                session.add(Category(name=cat["name"], slug=cat["slug"]))
        print("Categories seeded.")

        # Seed Subscription Plans
        for plan in PLANS_DATA:
            res = await session.execute(select(SubscriptionPlan).where(SubscriptionPlan.name == plan["name"]))
            if not res.scalars().first():
                session.add(SubscriptionPlan(**plan))
        print("Subscription plans seeded.")

        # Seed Content & Episodes
        for item in DEMO_CONTENT:
            episodes_data = item.pop("episodes", [])
            res = await session.execute(select(Content).where(Content.title == item["title"]))
            existing_content = res.scalars().first()

            if not existing_content:
                content_obj = Content(**item)
                session.add(content_obj)
                await session.flush()

                for ep in episodes_data:
                    episode_obj = Episode(series_id=content_obj.id, **ep)
                    session.add(episode_obj)
        print("Content catalog and episodes seeded.")

        await session.commit()
        print(" Seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_data())
