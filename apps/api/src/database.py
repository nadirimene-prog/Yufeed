import logging
import os
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import Pool
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
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql+asyncpg://"):
    ASYNC_DATABASE_URL = DATABASE_URL
elif DATABASE_URL.startswith("sqlite:///"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
else:
    # Fallback - assume the URL is already configured correctly
    ASYNC_DATABASE_URL = DATABASE_URL
    log.warning(f"Unknown database URL scheme, using as-is: {DATABASE_URL[:20]}...")

# ----------------------------------------------------------------------
# Async engine – uses asyncpg (PostgreSQL) or aiosqlite (SQLite)
# ----------------------------------------------------------------------
_is_sqlite = DATABASE_URL.startswith("sqlite")

_async_engine_kwargs = {
    "future": True,
}
# SQLite doesn't support connection pooling options or pool_pre_ping
if not _is_sqlite:
    _async_engine_kwargs.update(
        {
            "pool_pre_ping": True,
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_recycle": settings.DB_POOL_RECYCLE,
            "pool_timeout": settings.DB_POOL_TIMEOUT,
        }
    )

async_engine: AsyncEngine = create_async_engine(
    ASYNC_DATABASE_URL,
    **_async_engine_kwargs,
)


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
    _sync_engine_kwargs.update(
        {
            "pool_pre_ping": True,
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_recycle": settings.DB_POOL_RECYCLE,
            "pool_timeout": settings.DB_POOL_TIMEOUT,
        }
    )

_sync_engine: Engine | None = None


def get_sync_engine() -> Engine:
    """Lazily initialize sync engine to reduce import-time side effects."""
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = create_engine(DATABASE_URL, **_sync_engine_kwargs)
    return _sync_engine


class _SyncEngineProxy:
    """Backwards-compatible proxy that resolves the sync engine on first use."""

    def __getattr__(self, item):
        return getattr(get_sync_engine(), item)

    def __repr__(self) -> str:
        return repr(get_sync_engine())


sync_engine = _SyncEngineProxy()


class _LazySessionFactory:
    """Session factory that binds lazily to the sync engine."""

    def __init__(self) -> None:
        self._factory = sessionmaker(autocommit=False, autoflush=False)

    def _ensure_bind(self) -> None:
        if self._factory.kw.get("bind") is None:
            self._factory.configure(bind=get_sync_engine())

    def __call__(self, *args, **kwargs):
        self._ensure_bind()
        return self._factory(*args, **kwargs)

    def configure(self, **kwargs) -> None:
        self._factory.configure(**kwargs)

    @property
    def kw(self):
        return self._factory.kw


SessionLocal = _LazySessionFactory()

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

        Base.metadata.create_all(bind=get_sync_engine())
        _schema_initialized = True
    except Exception as e:
        log.warning("Failed to initialize test schema: %s", e)


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
