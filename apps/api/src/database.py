import logging
import os
from sqlalchemy import create_engine, event, exc
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.pool import Pool
from fastapi import HTTPException
from src.config import settings

log = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Original DATABASE_URL (e.g. postgresql://user:pw@host:5432/db)
# ----------------------------------------------------------------------
DATABASE_URL = settings.DATABASE_URL

# ----------------------------------------------------------------------
# Convert DATABASE_URL to async driver URL.
# PostgreSQL uses asyncpg, SQLite uses aiosqlite.
# ----------------------------------------------------------------------
if DATABASE_URL.startswith("postgresql://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace(
        "postgresql://", "postgresql+asyncpg://", 1
    )
elif DATABASE_URL.startswith("postgresql+asyncpg://"):
    ASYNC_DATABASE_URL = DATABASE_URL
elif DATABASE_URL.startswith("sqlite:///"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace(
        "sqlite:///", "sqlite+aiosqlite:///", 1
    )
else:
    # Fallback - assume the URL is already configured correctly
    ASYNC_DATABASE_URL = DATABASE_URL
    log.warning(f"Unknown database URL scheme, using as-is: {DATABASE_URL[:20]}...")

# ----------------------------------------------------------------------
# Async engine – uses asyncpg (PostgreSQL) or aiosqlite (SQLite)
# ----------------------------------------------------------------------
_is_sqlite = DATABASE_URL.startswith("sqlite")
async_engine: AsyncEngine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_pre_ping=True if not _is_sqlite else False,  # SQLite doesn't support pool_pre_ping
    future=True,
)

from sqlalchemy.ext.asyncio import AsyncSession

# ✅ CORRECT async session maker
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ----------------------------------------------------------------------
# Legacy sync engine – kept only for Alembic migrations and any old code
# ----------------------------------------------------------------------
_sync_engine_kwargs = {
    "echo": False,
}
# SQLite doesn't support connection pooling options
if not _is_sqlite:
    _sync_engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 10,
        "pool_recycle": 3600,
    })

sync_engine = create_engine(DATABASE_URL, **_sync_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

Base = declarative_base()

_schema_initialized = False


def _ensure_schema() -> None:
    """Create DB schema in test environments when using the sync engine."""
    global _schema_initialized
    if _schema_initialized:
        return
    if os.getenv("ENVIRONMENT", "").lower() not in {"test", "testing"}:
        return
    try:
        # Import models to register all tables before creating schema.
        import src.models  # noqa: F401
        Base.metadata.create_all(bind=sync_engine)
        _schema_initialized = True
    except Exception as exc:
        log.warning("Failed to initialize test schema: %s", exc)

# ----------------------------------------------------------------------
# Connection‑pool monitoring (useful for Prometheus / Grafana alerts)
# ----------------------------------------------------------------------
@event.listens_for(Pool, "connect")
def receive_connect(dbapi_conn, connection_record):
    log.debug("Database connection established")

@event.listens_for(Pool, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    log.debug("Connection checked out from pool")

# ----------------------------------------------------------------------
# Async dependency – used by FastAPI routes
# ----------------------------------------------------------------------
async def get_async_db():
    """
    Async DB session dependency.
    All new endpoints should depend on ``Depends(get_async_db)``.
    """
    async with AsyncSessionLocal() as session:
        yield session

# ----------------------------------------------------------------------
# Sync dependency – retained for Alembic and any legacy scripts.
# ----------------------------------------------------------------------
def get_sync_db():
    _ensure_schema()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db() -> "Session":
    _ensure_schema()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
