"""
Ingestion Configuration Module

Centralizes all configuration constants for the ingestion pipeline,
avoiding hardcoded values scattered across multiple files.
"""

from src.config import settings


class IngestionConfig:
    """Configuration constants for ingestion pipeline."""

    # HTTP request settings
    HTTP_TIMEOUT: float = getattr(settings, 'INGESTION_HTTP_TIMEOUT', 30.0)
    SPARQL_TIMEOUT: float = getattr(settings, 'INGESTION_SPARQL_TIMEOUT', 60.0)

    # Retry settings
    MAX_RETRIES: int = getattr(settings, 'INGESTION_MAX_RETRIES', 3)
    BASE_RETRY_DELAY: float = getattr(settings, 'INGESTION_RETRY_DELAY', 2.0)
    MAX_RETRY_DELAY: float = getattr(settings, 'INGESTION_MAX_RETRY_DELAY', 30.0)

    # Parallel processing
    PARALLEL_WORKERS: int = getattr(settings, 'INGESTION_WORKERS', 4)

    # Batch sizes
    BACKFILL_BATCH_SIZE: int = getattr(settings, 'INGESTION_BACKFILL_BATCH_SIZE', 50)
    BULK_CELEX_BATCH_SIZE: int = getattr(settings, 'INGESTION_BULK_CELEX_BATCH_SIZE', 100)

    # Task timeouts (in seconds)
    INGESTION_TASK_TIME_LIMIT: int = 3600  # 1 hour hard limit
    INGESTION_TASK_SOFT_TIME_LIMIT: int = 3000  # 50 min soft limit
    BACKFILL_TASK_TIME_LIMIT: int = 1800  # 30 min hard limit
    BACKFILL_TASK_SOFT_TIME_LIMIT: int = 1500  # 25 min soft limit

    # DLQ settings
    DLQ_MAX_RETRIES: int = getattr(settings, 'INGESTION_DLQ_MAX_RETRIES', 3)
    DLQ_RETRY_DELAY_HOURS: int = getattr(settings, 'INGESTION_DLQ_RETRY_DELAY_HOURS', 6)


# Singleton instance for easy access
ingestion_config = IngestionConfig()
