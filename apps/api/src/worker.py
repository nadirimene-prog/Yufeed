import logging
import os
from celery import Celery
from celery.schedules import crontab
from src.config import settings
from src.database import SessionLocal
from src.ingestion.manager import IngestionManager
from src.email_service import send_email

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Celery App
# We use the redis url from settings
celery_app = Celery("worker", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "weekly-ingestion-task": {
            "task": "src.worker.run_ingestion",
            "schedule": crontab(minute=0, hour=8, day_of_week=1),  # Weekly Monday 08:00 UTC
        },
        # Phase 4B: Feature Store Automation
        "refresh-active-users-features": {
            "task": "tasks.refresh_active_users_features",
            "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours
            "args": (30, 100, 1),  # days, batch_size, version
        },
        "monitor-feature-staleness": {
            "task": "tasks.monitor_feature_staleness",
            "schedule": crontab(minute=0, hour="*/12"),  # Every 12 hours
            "args": (24,),  # staleness_threshold_hours
        },
        "compute-feature-importance": {
            "task": "tasks.compute_feature_importance",
            "schedule": crontab(minute=0, hour=3, day_of_week=1),  # Weekly on Monday 3 AM
            "args": ("models/alert_triage/latest.joblib",),
        },
    },
)

@celery_app.task
def run_ingestion():
    """
    Celery task to run the weekly ingestion process.
    """
    logger.info("Starting scheduled ingestion task via Celery")
    db = SessionLocal()
    try:
        manager = IngestionManager(db)
        manager.run_weekly_ingestion()
        
        # Send notification
        try:
            send_email(
                "user@example.com", 
                "Weekly EU Legal Digest", 
                "Ingestion ran successfully. Access dashboard to view new documents."
            )
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            
    except Exception as e:
        logger.error(f"Ingestion task failed: {e}")
        # We could re-raise to let Celery retry, but for now we verify failure in logs
        raise e
    finally:
        db.close()
    logger.info("Ingestion task completed")
