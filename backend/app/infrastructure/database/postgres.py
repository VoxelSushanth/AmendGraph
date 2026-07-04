"""
PostgreSQL database connection and session management.

Uses SQLAlchemy for ORM with async support.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy import create_engine as sync_create_engine

from app.core.config import get_settings

settings = get_settings()

# Async engine for API operations
async_engine: AsyncEngine | None = None
async_session_maker: async_sessionmaker[AsyncSession] | None = None

# Sync engine for migrations and scripts
sync_engine = sync_create_engine(settings.database_url, echo=settings.debug)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


def init_db() -> None:
    """Initialize database connections."""
    global async_engine, async_session_maker

    async_engine = create_async_engine(
        settings.async_database_url,
        echo=settings.debug,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session from the pool.

    Usage:
        async with get_db_session() as session:
            # use session
    """
    if async_session_maker is None:
        init_db()

    session = async_session_maker()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


def get_sync_session() -> Session:
    """Get a synchronous database session."""
    return Session(sync_engine)
