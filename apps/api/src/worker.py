"""
Celery Worker Configuration

Handles scheduled tasks for:
- Weekly regulatory document ingestion
- Feature store updates
- Alert triage model training
"""
import logging
import traceback
from celery import Celery
from celery.schedules import crontab

from src.config import settings
from src.database import SessionLocal
from src.ingestion.manager import IngestionManager
from src.ingestion.alerts import send_ingestion_failure_alert

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Celery App
celery_app = Celery("worker", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Retry configuration
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Beat schedule
    beat_schedule={
        "weekly-ingestion-task": {
            "task": "src.worker.run_ingestion",
            "schedule": crontab(minute=0, hour=8, day_of_week=1),  # Monday 08:00 UTC
        },
        # Phase 4B: Feature Store Automation
        "refresh-active-users-features": {
            "task": "tasks.refresh_active_users_features",
            "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours
            "args": (30, 100, 1),
        },
        "monitor-feature-staleness": {
            "task": "tasks.monitor_feature_staleness",
            "schedule": crontab(minute=0, hour="*/12"),  # Every 12 hours
            "args": (24,),
        },
        "compute-feature-importance": {
            "task": "tasks.compute_feature_importance",
            "schedule": crontab(minute=0, hour=3, day_of_week=1),  # Monday 3 AM
            "args": ("models/alert_triage/latest.joblib",),
        },
    },
)


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=300,  # 5 minutes
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def run_ingestion(self):
    """
    Celery task to run the weekly ingestion process.

    Features:
    - Automatic retry on transient failures
    - Email alerts on success/failure
    - Detailed logging for monitoring
    """
    logger.info("Starting scheduled ingestion task via Celery")
    db = SessionLocal()

    try:
        manager = IngestionManager(db)
        reports = manager.run_weekly_ingestion(send_alerts=True)

        # Log summary
        total_new = sum(r.items_new for r in reports)
        total_updated = sum(r.items_updated for r in reports)
        total_errors = sum(len(r.errors) for r in reports)

        logger.info(
            f"Ingestion completed: {total_new} new, {total_updated} updated, "
            f"{total_errors} errors across {len(reports)} sources"
        )

        # Return summary for Celery result backend
        return {
            "status": "completed",
            "sources_processed": len(reports),
            "total_new": total_new,
            "total_updated": total_updated,
            "total_errors": total_errors,
        }

    except Exception as e:
        error_msg = f"Ingestion task failed: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)

        # Send critical failure alert
        try:
            send_ingestion_failure_alert(
                source_name="Scheduled Ingestion",
                error_message=error_msg,
            )
        except Exception as alert_error:
            logger.error(f"Failed to send failure alert: {alert_error}")

        # Re-raise to trigger Celery retry
        raise

    finally:
        db.close()


@celery_app.task
def run_manual_ingestion(source_keys: list = None, days_back: int = 30):
    """
    Manual ingestion task for ad-hoc runs.

    Args:
        source_keys: List of source keys to process (None = all)
        days_back: Number of days to look back

    Example:
        run_manual_ingestion.delay(["eur-lex-oj-en"], 7)
    """
    from datetime import datetime, timedelta, timezone

    logger.info(f"Starting manual ingestion: sources={source_keys}, days_back={days_back}")
    db = SessionLocal()

    try:
        manager = IngestionManager(db)

        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days_back)

        reports = manager.run_manual_ingestion(
            source_keys=source_keys,
            start_date=start_date,
            end_date=end_date,
            send_alerts=True,
        )

        total_new = sum(r.items_new for r in reports)
        total_updated = sum(r.items_updated for r in reports)

        logger.info(f"Manual ingestion completed: {total_new} new, {total_updated} updated")

        return {
            "status": "completed",
            "sources_processed": len(reports),
            "total_new": total_new,
            "total_updated": total_updated,
        }

    except Exception as e:
        logger.error(f"Manual ingestion failed: {e}")
        raise

    finally:
        db.close()


@celery_app.task
def test_ingestion_alerts():
    """Test task to verify email alerting is working."""
    from src.ingestion.alerts import send_ingestion_report, IngestionReport
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)

    test_reports = [
        IngestionReport(
            source_name="Test Source",
            status="completed",
            started_at=now,
            completed_at=now,
            items_seen=10,
            items_new=5,
            items_updated=3,
            items_skipped=2,
            errors=[],
        )
    ]

    success = send_ingestion_report(test_reports)
    return {"email_sent": success}
