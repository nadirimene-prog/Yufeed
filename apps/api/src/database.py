import logging
from sqlalchemy import create_engine, event, exc
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import Pool
from fastapi import HTTPException
from src.config import settings

logger = logging.getLogger(__name__)

DATABASE_URL = settings.DATABASE_URL

# Create engine with connection pooling and error handling
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using them
    pool_size=5,  # Maximum number of connections to keep
    max_overflow=10,  # Maximum overflow connections
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=False  # Set to True for SQL debugging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Connection pool event handlers for monitoring
@event.listens_for(Pool, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Log successful database connections."""
    logger.debug("Database connection established")


@event.listens_for(Pool, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Verify connection is alive before checkout."""
    logger.debug("Connection checked out from pool")


def get_db():
    """
    Database session dependency with proper error handling.

    Yields:
        Session: SQLAlchemy database session

    Raises:
        HTTPException: 503 if database is unavailable
        HTTPException: 500 for other database errors
    """
    db = None
    try:
        db = SessionLocal()
        yield db
        # Commit if no exceptions occurred
        db.commit()
    except HTTPException:
        if db:
            db.rollback()
        raise
    except exc.OperationalError as e:
        # Database connection issues (DB down, network issues, etc.)
        logger.error(f"Database connection error: {e}", exc_info=True)
        if db:
            db.rollback()
        raise HTTPException(
            status_code=503,
            detail="Database service unavailable. Please try again later."
        )
    except exc.IntegrityError as e:
        # Constraint violations (unique, foreign key, etc.)
        logger.warning(f"Database integrity error: {e}")
        if db:
            db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Data integrity violation. Please check your input."
        )
    except exc.DBAPIError as e:
        # Other database API errors
        logger.error(f"Database API error: {e}", exc_info=True)
        if db:
            db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Database error occurred. Please contact support."
        )
    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception(f"Unexpected database error: {e}")
        if db:
            db.rollback()
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again."
        )
    finally:
        if db:
            db.close()
            logger.debug("Database connection closed")
