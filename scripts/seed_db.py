import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from app.core.security import hash_password
from app.db.models import User
from app.db.session import AsyncSessionLocal


async def seed_database():
    print("Seeding database...")
    async with AsyncSessionLocal() as session:
        users = [
            ("admin@pragatibharti.edu", "AdminPass123!", "admin"),
            ("reviewer@pragatibharti.edu", "ReviewerPass123!", "reviewer"),
            ("teacher@pragatibharti.edu", "TeacherPass123!", "user"),
            ("student@pragatibharti.edu", "StudentPass123!", "user"),
        ]

        for email, password, role in users:
            stmt = select(User).where(User.email == email)
            res = await session.execute(stmt)
            existing = res.scalars().first()
            if not existing:
                u = User(
                    email=email,
                    password_hash=hash_password(password),
                    role=role,
                    is_active=True,
                )
                session.add(u)
                print(f"Created {role}: {email}")
            else:
                print(f"User {email} already exists")

        await session.commit()
    print("Database seeding completed.")


if __name__ == "__main__":
    asyncio.run(seed_database())
