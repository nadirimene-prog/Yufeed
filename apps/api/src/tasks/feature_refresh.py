"""
Feature Store Refresh Tasks
Phase 4B: Task 5.3 - Automated Feature Store Updates

Celery tasks for periodic feature updates:
- Refresh features for active users
- Incremental feature computation
- Feature versioning
- Staleness monitoring
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from celery import Task
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from src.worker import celery_app
from src.database import SessionLocal
from src.models.transaction_models import Transaction, UserRiskProfile, FeatureValue
from src.services.feature_store import FeatureStoreService
from src.services.time_series_features import TimeSeriesFeatureExtractor

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="tasks.refresh_user_features")
def refresh_user_features(self: Task, user_id: str, version: int = 1) -> Dict[str, Any]:
    """
    Refresh features for a specific user.

    Args:
        user_id: User identifier
        version: Feature version number

    Returns:
        Dictionary with refresh status and metrics
    """
    db = SessionLocal()
    try:
        logger.info(f"Refreshing features for user {user_id} (version {version})")

        # Extract time-series features
        ts_extractor = TimeSeriesFeatureExtractor(db)
        current_time = datetime.utcnow()

        features = ts_extractor.extract_features(
            user_id=user_id,
            current_time=current_time,
            lookback_days=90
        )

        # Store in feature store
        feature_store = FeatureStoreService(db)

        feature_dict = {
            name: {
                "value": value,
                "feature_type": "time_series",
                "calculated_at": current_time,
                "version": version
            }
            for name, value in features.items()
        }

        feature_store.upsert_features(
            entity_type="user",
            entity_id=user_id,
            features=feature_dict
        )

        db.commit()

        logger.info(f"Refreshed {len(features)} features for user {user_id}")

        return {
            "user_id": user_id,
            "feature_count": len(features),
            "version": version,
            "refreshed_at": current_time.isoformat(),
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Failed to refresh features for user {user_id}: {e}", exc_info=True)
        db.rollback()
        return {
            "user_id": user_id,
            "status": "error",
            "error": str(e)
        }
    finally:
        db.close()


@celery_app.task(bind=True, name="tasks.refresh_active_users_features")
def refresh_active_users_features(
    self: Task,
    days: int = 30,
    batch_size: int = 100,
    version: int = 1
) -> Dict[str, Any]:
    """
    Refresh features for all users active in the last N days.

    Args:
        days: Lookback window for active users
        batch_size: Number of users to process per batch
        version: Feature version number

    Returns:
        Summary of refresh operation
    """
    db = SessionLocal()
    try:
        logger.info(f"Refreshing features for users active in last {days} days")

        # Find active users
        start_date = datetime.utcnow() - timedelta(days=days)

        active_users = db.query(Transaction.user_id).filter(
            Transaction.timestamp >= start_date
        ).group_by(Transaction.user_id).all()

        user_ids = [user[0] for user in active_users]

        logger.info(f"Found {len(user_ids)} active users")

        # Process in batches
        total_success = 0
        total_errors = 0

        for i in range(0, len(user_ids), batch_size):
            batch = user_ids[i:i + batch_size]

            for user_id in batch:
                try:
                    # Queue individual refresh task
                    refresh_user_features.delay(user_id, version=version)
                    total_success += 1
                except Exception as e:
                    logger.error(f"Failed to queue refresh for user {user_id}: {e}")
                    total_errors += 1

        return {
            "total_users": len(user_ids),
            "queued": total_success,
            "errors": total_errors,
            "batch_size": batch_size,
            "version": version,
            "started_at": datetime.utcnow().isoformat(),
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"Failed to refresh active users features: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        db.close()


@celery_app.task(bind=True, name="tasks.monitor_feature_staleness")
def monitor_feature_staleness(
    self: Task,
    staleness_threshold_hours: int = 24
) -> Dict[str, Any]:
    """
    Monitor feature staleness and identify users needing refresh.

    Args:
        staleness_threshold_hours: Hours before features are considered stale

    Returns:
        Staleness report with recommended actions
    """
    db = SessionLocal()
    try:
        logger.info("Monitoring feature staleness")

        staleness_threshold = datetime.utcnow() - timedelta(hours=staleness_threshold_hours)

        # Find stale features
        stale_features = db.query(
            FeatureValue.entity_id,
            func.max(FeatureValue.calculated_at).label('last_updated')
        ).filter(
            and_(
                FeatureValue.entity_type == 'user',
                FeatureValue.calculated_at < staleness_threshold
            )
        ).group_by(FeatureValue.entity_id).all()

        stale_user_ids = [row.entity_id for row in stale_features]

        logger.info(f"Found {len(stale_user_ids)} users with stale features")

        # Check if users are still active
        active_stale_users = []
        for user_id in stale_user_ids:
            recent_txns = db.query(func.count(Transaction.id)).filter(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.timestamp >= staleness_threshold
                )
            ).scalar()

            if recent_txns > 0:
                active_stale_users.append(user_id)

        logger.info(f"Found {len(active_stale_users)} active users with stale features")

        # Queue refresh for active stale users
        for user_id in active_stale_users:
            refresh_user_features.delay(user_id)

        return {
            "total_stale": len(stale_user_ids),
            "active_stale": len(active_stale_users),
            "queued_for_refresh": len(active_stale_users),
            "staleness_threshold_hours": staleness_threshold_hours,
            "checked_at": datetime.utcnow().isoformat(),
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"Failed to monitor feature staleness: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        db.close()


@celery_app.task(bind=True, name="tasks.compute_feature_importance")
def compute_feature_importance(
    self: Task,
    model_path: str = "models/alert_triage/latest.joblib"
) -> Dict[str, Any]:
    """
    Compute and track feature importance from ML model.

    Args:
        model_path: Path to trained model

    Returns:
        Feature importance rankings
    """
    try:
        logger.info("Computing feature importance")

        # Load model
        import joblib
        from pathlib import Path

        model_file = Path(model_path)
        if not model_file.exists():
            logger.warning(f"Model not found: {model_path}")
            return {"status": "error", "error": "Model not found"}

        model = joblib.load(model_file)

        # Get feature importance
        if hasattr(model, 'feature_importances_'):
            importances = model.feature_importances_
            feature_names = getattr(model, 'feature_names_in_', [f'feature_{i}' for i in range(len(importances))])

            # Sort by importance
            importance_dict = dict(zip(feature_names, importances))
            sorted_importance = dict(
                sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)
            )

            # Top 20 features
            top_features = dict(list(sorted_importance.items())[:20])

            logger.info(f"Top 5 features: {list(top_features.keys())[:5]}")

            return {
                "top_features": top_features,
                "total_features": len(feature_names),
                "model_path": model_path,
                "computed_at": datetime.utcnow().isoformat(),
                "status": "success"
            }
        else:
            return {
                "status": "error",
                "error": "Model does not support feature importance"
            }

    except Exception as e:
        logger.error(f"Failed to compute feature importance: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


# Periodic task configuration
# Add to celery beat schedule in src/worker.py:
"""
celery_app.conf.beat_schedule = {
    'refresh-active-users-features': {
        'task': 'tasks.refresh_active_users_features',
        'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
        'args': (30, 100, 1),  # days, batch_size, version
    },
    'monitor-feature-staleness': {
        'task': 'tasks.monitor_feature_staleness',
        'schedule': crontab(minute=0, hour='*/12'),  # Every 12 hours
        'args': (24,),  # staleness_threshold_hours
    },
    'compute-feature-importance': {
        'task': 'tasks.compute_feature_importance',
        'schedule': crontab(minute=0, hour=3, day_of_week=1),  # Weekly on Monday 3 AM
        'args': ('models/alert_triage/latest.joblib',),
    },
}
"""
