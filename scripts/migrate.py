#!/usr/bin/env python3
"""
Apply database migrations.

Fresh databases (no alembic_version, no users table) are bootstrapped from
current SQLAlchemy models, then stamped to head. Existing databases run
`alembic upgrade head` as usual.
"""
from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.db.session import engine  # noqa: E402
from app.models import Base  # noqa: E402


async def table_exists(conn, table_name: str) -> bool:
    result = await conn.execute(
        text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.tables "
            "  WHERE table_schema = 'public' AND table_name = :table_name"
            ")"
        ),
        {"table_name": table_name},
    )
    return bool(result.scalar())


async def is_fresh_database() -> bool:
    async with engine.connect() as conn:
        has_alembic = await table_exists(conn, "alembic_version")
        has_users = await table_exists(conn, "users")
        return not has_alembic and not has_users


async def bootstrap_fresh_database() -> None:
    print("Fresh database detected — creating schema from models")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    subprocess.run(["alembic", "stamp", "head"], check=True)
    print("Database bootstrapped and stamped to head")


def upgrade_existing_database() -> None:
    print("Existing database detected — running alembic upgrade head")
    subprocess.run(["alembic", "upgrade", "head"], check=True)


async def main() -> None:
    try:
        if await is_fresh_database():
            await bootstrap_fresh_database()
        else:
            upgrade_existing_database()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
