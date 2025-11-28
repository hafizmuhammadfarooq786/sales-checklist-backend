"""
PyTest configuration and fixtures for Sales Checklist™ Backend tests
"""
import pytest
import pytest_asyncio
import asyncio
from typing import Generator, AsyncGenerator
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.session import get_db
from app.models.base import Base
from app.models.user import User, UserRole
from app.services.auth_service import auth_service


# Test database setup - Using async SQLite with aiosqlite
SQLALCHEMY_TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
TestingSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """
    Create a fresh database for each test.
    Provides transaction isolation with async support.
    """
    # Create all tables using async context
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create async session
    async with TestingSessionLocal() as session:
        yield session
        await session.commit()

    # Drop all tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    """
    Create a test client with async database override.
    """
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session):
    """
    Create a test user in the database.
    """
    user = User(
        email="test@example.com",
        password_hash=auth_service.hash_password("Test123!@#"),
        first_name="Test",
        last_name="User",
        role=UserRole.REP,
        is_active=True,
        is_verified=True,
        failed_login_attempts=0
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session):
    """
    Create an admin user in the database.
    """
    user = User(
        email="admin@example.com",
        password_hash=auth_service.hash_password("Admin123!@#"),
        first_name="Admin",
        last_name="User",
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
        failed_login_attempts=0
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user):
    """
    Get authentication headers for test user.
    """
    token = auth_service.create_access_token({"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_headers(admin_user):
    """
    Get authentication headers for admin user.
    """
    token = auth_service.create_access_token({"sub": str(admin_user.id)})
    return {"Authorization": f"Bearer {token}"}
