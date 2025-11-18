"""
Initialize database - create all tables
Run this script to set up the database for the first time
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.models.base import Base
from app.models import (
    User, Organization, Team,
    ChecklistCategory, ChecklistItem, CoachingQuestion,
    Session, AudioFile, Transcript, SessionResponse,
    ScoringResult, CoachingFeedback,
    Report, SalesforceSync,
    AuditLog, Setting
)

async def init_database():
    """Create all database tables"""
    print("Connecting to database...")
    print(f"Database URL: {settings.DATABASE_URL[:50]}...")

    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=True,
    )

    async with engine.begin() as conn:
        print("Dropping all tables...")
        await conn.run_sync(Base.metadata.drop_all)

        print("Creating all tables...")
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()
    print("✅ Database initialized successfully!")
    print("All tables created.")

if __name__ == "__main__":
    asyncio.run(init_database())
