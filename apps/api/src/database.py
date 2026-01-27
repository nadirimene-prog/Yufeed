import logging
import os
from sqlalchemy import create_engine, event, exc
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
# Convert it to the async‑pg URL that SQLAlchemy expects.
# If the URL already contains "+asyncpg" we leave it unchanged.
# ----------------------------------------------------------------------
if DATABASE_URL.startswith("postgresql://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace(
        "postgresql://", "postgresql+asyncpg://", 1
    )
else:
    ASYNC_DATABASE_URL = DATABASE_URL

# ----------------------------------------------------------------------
# Async engine – uses asyncpg driver
# ----------------------------------------------------------------------
async_engine: AsyncEngine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

# ✅ CORRECT async session maker
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=Session,
    expire_on_commit=False,
)

# ----------------------------------------------------------------------
# Legacy sync engine – kept only for Alembic migrations and any old code
# ----------------------------------------------------------------------
sync_engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

Base = declarative_base()

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
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
