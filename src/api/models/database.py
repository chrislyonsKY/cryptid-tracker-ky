"""
Database session factories for PostgreSQL (async) and MySQL (async).

Provides dependency-injectable session generators for FastAPI routes.
"""

import logging
import ssl

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.config import settings

logger = logging.getLogger(__name__)

# --- PostgreSQL + PostGIS (async via asyncpg) ---

# Strip ssl/sslmode params from URI — asyncpg doesn't understand them as query params
_pg_uri = (
    settings.pg_uri
    .replace("?ssl=require", "")
    .replace("&ssl=require", "")
    .replace("?sslmode=require", "")
    .replace("&sslmode=require", "")
)

# Create SSL context for asyncpg (Aiven PostgreSQL requires SSL)
_pg_ssl = ssl.create_default_context()
_pg_ssl.check_hostname = False
_pg_ssl.verify_mode = ssl.CERT_NONE

pg_engine = create_async_engine(
    _pg_uri,
    echo=settings.debug,
    pool_size=3,
    max_overflow=5,
    pool_recycle=300,
    pool_pre_ping=True,
    connect_args={"ssl": _pg_ssl},
)

AsyncSessionLocal = async_sessionmaker(
    pg_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """Yield an async PostgreSQL session. For use as a FastAPI dependency."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# --- MySQL (async via aiomysql) ---

# Aiven MySQL requires SSL; strip ?ssl=true from URI (handled via connect_args)
_mysql_uri = settings.mysql_uri.split("?")[0]

_mysql_ssl = ssl.create_default_context()
_mysql_ssl.check_hostname = False
_mysql_ssl.verify_mode = ssl.CERT_NONE

try:
    mysql_engine = create_async_engine(
        _mysql_uri,
        echo=settings.debug,
        pool_size=2,
        max_overflow=3,
        pool_recycle=300,
        pool_pre_ping=True,
        connect_args={"ssl": _mysql_ssl},
    )
except Exception as e:
    logger.warning("MySQL engine creation failed (community features disabled): %s", e)
    mysql_engine = None

AsyncMySQLSession = None
if mysql_engine:
    AsyncMySQLSession = async_sessionmaker(
        mysql_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_mysql_db() -> AsyncSession:
    """Yield an async MySQL session. For use as a FastAPI dependency."""
    if not AsyncMySQLSession:
        raise RuntimeError("MySQL not available")
    async with AsyncMySQLSession() as session:
        try:
            yield session
        finally:
            await session.close()
