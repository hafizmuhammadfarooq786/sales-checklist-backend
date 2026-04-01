"""
Database session configuration
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings


def _async_connect_args(database_url: str) -> dict:
    """Disable asyncpg prepared-statement cache (stale plans after DDL / migrations)."""
    if "+asyncpg" in database_url:
        return {"statement_cache_size": 0}
    return {}


# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    future=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args=_async_connect_args(settings.DATABASE_URL),
)

# Create session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """
    Dependency to get database session.
    Usage in FastAPI endpoints:
        async def endpoint(db: AsyncSession = Depends(get_db)):
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_db_session() -> AsyncSession:
    """
    Get database session for background tasks.
    Usage in background tasks:
        async with get_db_session() as db:
            # database operations
    """
    return AsyncSessionLocal()
