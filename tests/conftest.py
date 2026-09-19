import asyncio
from pathlib import Path
import sys
from typing import AsyncGenerator
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.main import app
from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.models import User
from app.db.session import get_db

settings.APP_ENV = "test"

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestAsyncSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    u = User(
        email="testuser@pragatibharti.edu",
        password_hash=hash_password("UserPass123!"),
        role="user",
        is_active=True,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest.fixture
async def other_user(db_session: AsyncSession) -> User:
    u = User(
        email="otheruser@pragatibharti.edu",
        password_hash=hash_password("OtherPass123!"),
        role="user",
        is_active=True,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest.fixture
async def reviewer_user(db_session: AsyncSession) -> User:
    u = User(
        email="testreviewer@pragatibharti.edu",
        password_hash=hash_password("ReviewerPass123!"),
        role="reviewer",
        is_active=True,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    u = User(
        email="testadmin@pragatibharti.edu",
        password_hash=hash_password("AdminPass123!"),
        role="admin",
        is_active=True,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest.fixture
def user_token(test_user: User) -> str:
    return create_access_token({"sub": test_user.id, "email": test_user.email, "role": test_user.role})


@pytest.fixture
def other_user_token(other_user: User) -> str:
    return create_access_token({"sub": other_user.id, "email": other_user.email, "role": other_user.role})


@pytest.fixture
def reviewer_token(reviewer_user: User) -> str:
    return create_access_token({"sub": reviewer_user.id, "email": reviewer_user.email, "role": reviewer_user.role})


@pytest.fixture
def admin_token(admin_user: User) -> str:
    return create_access_token({"sub": admin_user.id, "email": admin_user.email, "role": admin_user.role})
