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
        "daily-ingestion-task": {
            "task": "src.worker.run_ingestion",
            "schedule": crontab(hour=8, minute=0),  # Run daily at 8 AM UTC
        },
    },
)

@celery_app.task
def run_ingestion():
    """
    Celery task to run the daily ingestion process.
    """
    logger.info("Starting scheduled ingestion task via Celery")
    db = SessionLocal()
    try:
        manager = IngestionManager(db)
        manager.run_daily_ingestion()
        
        # Send notification
        try:
            send_email(
                "user@example.com", 
                "Daily EU Legal Digest", 
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
