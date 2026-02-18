"""
Transaction Processing Tasks

Moves transaction risk scoring + rule evaluation off of request-scoped background tasks
and into Celery, ensuring per-tenant isolation and safe DB session handling.
"""

import logging
import traceback
from typing import Any, Dict, List, Optional

from celery import Task
from celery.exceptions import MaxRetriesExceededError
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.models.transaction_models import Transaction, Alert, FailedTransactionProcessingItem
from src.services.risk_scoring import RiskScoringService
from src.services.rules_engine import RulesEngine
from src.services.customer_lifecycle import CustomerLifecycleService
from src.tenancy.context import TenantContext
from src.utils.time import utc_now
from src.worker import celery_app

logger = logging.getLogger(__name__)

TRANSIENT_EXCEPTIONS = (OperationalError,)


def _upsert_failed_processing_item(
    db: Session,
    *,
    tenant_id: str,
    transaction_db_id: int,
    transaction_id: Optional[str],
    error_message: str,
    error_traceback: str,
    retry_count: int,
    max_retries: int,
    status: str,
    payload: Optional[Dict[str, Any]] = None,
) -> FailedTransactionProcessingItem:
    existing = (
        db.query(FailedTransactionProcessingItem)
        .filter(
            FailedTransactionProcessingItem.tenant_id == tenant_id,
            FailedTransactionProcessingItem.transaction_db_id == transaction_db_id,
            FailedTransactionProcessingItem.status.in_(["pending", "exhausted"]),
        )
        .order_by(FailedTransactionProcessingItem.created_at.desc())
        .first()
    )

    item = existing or FailedTransactionProcessingItem(
        tenant_id=tenant_id,
        transaction_db_id=transaction_db_id,
        created_at=utc_now(),
    )

    item.transaction_id = transaction_id
    item.error_message = error_message
    item.error_traceback = error_traceback
    item.payload_json = payload
    item.retry_count = retry_count
    item.max_retries = max_retries
    item.status = status
    item.last_retry_at = utc_now() if retry_count else None

    db.add(item)
    return item


def process_transaction_sync(db: Session, transaction_db_id: int, tenant_id: str) -> Dict[str, Any]:
    """
    Synchronous transaction processing helper.

    This is used by the Celery task and can also be invoked synchronously in tests.
    """
    transaction = (
        db.query(Transaction)
        .filter(
            Transaction.id == transaction_db_id,
            Transaction.tenant_id == tenant_id,
        )
        .first()
    )
    if not transaction:
        return {
            "status": "not_found",
            "transaction_db_id": transaction_db_id,
            "tenant_id": tenant_id,
        }

    risk_service = RiskScoringService(db)
    rules_engine = RulesEngine(db)

    risk_score = risk_service.score_transaction(transaction_db_id)
    transaction.risk_score = risk_score
    transaction.risk_level = risk_service.get_risk_level(risk_score)

    # Evaluate rule-based alerts
    alerts: List[Alert] = rules_engine.evaluate_transaction(transaction_db_id)
    velocity_alerts: List[Alert] = rules_engine.evaluate_velocity_rules(
        transaction.user_id, tenant_id=tenant_id
    )

    # Update user risk profile (tenant scoped)
    risk_service.update_user_risk_profile(transaction.user_id, tenant_id=tenant_id)

    lifecycle_service = CustomerLifecycleService(db)
    lifecycle_service.sync_kyc_to_risk_profile(transaction.user_id, tenant_id=tenant_id)
    edd_result = lifecycle_service.trigger_edd_from_transactions(
        transaction_db_id=transaction_db_id,
        tenant_id=tenant_id,
    )

    db.commit()

    return {
        "status": "success",
        "tenant_id": tenant_id,
        "transaction_db_id": transaction_db_id,
        "transaction_id": transaction.transaction_id,
        "risk_score": float(risk_score),
        "alerts_created": len(alerts) + len(velocity_alerts),
        "edd_triggered": bool(edd_result.get("triggered")),
    }


@celery_app.task(bind=True, name="tasks.process_transaction_task")
def process_transaction_task(self: Task, transaction_db_id: int, tenant_id: str) -> Dict[str, Any]:
    """
    Celery task to process a transaction with full tenant isolation.

    Args:
        transaction_db_id: Internal DB PK for the transaction
        tenant_id: Tenant identifier
    """
    db = SessionLocal()
    try:
        with TenantContext(tenant_id):
            return process_transaction_sync(db, transaction_db_id, tenant_id)
    except TRANSIENT_EXCEPTIONS as exc:
        db.rollback()
        retries = int(getattr(getattr(self, "request", None), "retries", 0) or 0)
        countdown = min(300 * (2**retries), 1800)  # 5m, 10m, 20m (cap 30m)
        try:
            raise self.retry(exc=exc, countdown=countdown, max_retries=3)
        except MaxRetriesExceededError:
            # Persist to DLQ after exhausting retries.
            tx = (
                db.query(Transaction)
                .filter(Transaction.id == transaction_db_id, Transaction.tenant_id == tenant_id)
                .first()
            )
            item = _upsert_failed_processing_item(
                db,
                tenant_id=tenant_id,
                transaction_db_id=transaction_db_id,
                transaction_id=tx.transaction_id if tx else None,
                error_message=str(exc),
                error_traceback=traceback.format_exc(),
                retry_count=retries,
                max_retries=3,
                status="exhausted",
                payload={"exception_type": type(exc).__name__},
            )
            db.commit()
            return {
                "status": "dlq",
                "tenant_id": tenant_id,
                "transaction_db_id": transaction_db_id,
                "dlq_item_id": item.id,
                "error": str(exc),
            }
    except DBAPIError as exc:
        # Retry only if the connection was invalidated (transient DB connectivity issue).
        if getattr(exc, "connection_invalidated", False):
            db.rollback()
            retries = int(getattr(getattr(self, "request", None), "retries", 0) or 0)
            countdown = min(300 * (2**retries), 1800)
            try:
                raise self.retry(exc=exc, countdown=countdown, max_retries=3)
            except MaxRetriesExceededError:
                tx = (
                    db.query(Transaction)
                    .filter(Transaction.id == transaction_db_id, Transaction.tenant_id == tenant_id)
                    .first()
                )
                item = _upsert_failed_processing_item(
                    db,
                    tenant_id=tenant_id,
                    transaction_db_id=transaction_db_id,
                    transaction_id=tx.transaction_id if tx else None,
                    error_message=str(exc),
                    error_traceback=traceback.format_exc(),
                    retry_count=retries,
                    max_retries=3,
                    status="exhausted",
                    payload={"exception_type": type(exc).__name__},
                )
                db.commit()
                return {
                    "status": "dlq",
                    "tenant_id": tenant_id,
                    "transaction_db_id": transaction_db_id,
                    "dlq_item_id": item.id,
                    "error": str(exc),
                }
        raise
    except Exception as exc:
        logger.error(
            "Transaction processing failed tenant=%s transaction_db_id=%s: %s",
            tenant_id,
            transaction_db_id,
            exc,
            exc_info=True,
        )
        db.rollback()

        tx = (
            db.query(Transaction)
            .filter(Transaction.id == transaction_db_id, Transaction.tenant_id == tenant_id)
            .first()
        )
        retries = int(getattr(getattr(self, "request", None), "retries", 0) or 0)
        item = _upsert_failed_processing_item(
            db,
            tenant_id=tenant_id,
            transaction_db_id=transaction_db_id,
            transaction_id=tx.transaction_id if tx else None,
            error_message=str(exc),
            error_traceback=traceback.format_exc(),
            retry_count=retries,
            max_retries=3,
            status="exhausted",
            payload={"exception_type": type(exc).__name__},
        )
        try:
            db.commit()
        except Exception:
            db.rollback()
        return {
            "status": "dlq",
            "tenant_id": tenant_id,
            "transaction_db_id": transaction_db_id,
            "dlq_item_id": getattr(item, "id", None),
            "error": str(exc),
        }
    finally:
        db.close()
