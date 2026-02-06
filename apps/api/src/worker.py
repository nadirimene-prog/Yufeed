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

# Cron parser for 5-field expressions (min hour dom mon dow).
def _safe_crontab(expression: str, fallback: crontab) -> crontab:
    parts = [part for part in (expression or "").split() if part]
    if len(parts) != 5:
        logger.warning(f"Invalid cron '{expression}'. Using fallback schedule.")
        return fallback
    minute, hour, day_of_month, month_of_year, day_of_week = parts
    try:
        return crontab(
            minute=minute,
            hour=hour,
            day_of_month=day_of_month,
            month_of_year=month_of_year,
            day_of_week=day_of_week,
        )
    except Exception as exc:
        logger.warning(f"Failed to parse cron '{expression}': {exc}. Using fallback schedule.")
        return fallback

CONTENT_BACKFILL_SCHEDULE = _safe_crontab(
    settings.CONTENT_BACKFILL_SCHEDULE,
    crontab(minute=0, hour=2, day_of_month=1),
)

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
        "content-backfill-task": {
            "task": "src.worker.run_content_backfill",
            "schedule": CONTENT_BACKFILL_SCHEDULE,
        },
        # Phase 4B: Feature Store Automation
        "refresh-active-users-features": {
            "task": "tasks.refresh_active_users_features_all_tenants",
            "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours
            "args": (30, 100, 1),
        },
        "monitor-feature-staleness": {
            "task": "tasks.monitor_feature_staleness_all_tenants",
            "schedule": crontab(minute=0, hour="*/12"),  # Every 12 hours
            "args": (24,),
        },
        "compute-feature-importance": {
            "task": "tasks.compute_feature_importance",
            "schedule": crontab(minute=0, hour=3, day_of_week=1),  # Monday 3 AM
            "args": ("models/alert_triage/latest.joblib",),
        },
        # Compliance deadline alerts - daily at 9 AM UTC
        "check-obligation-deadlines": {
            "task": "src.worker.check_obligation_deadlines",
            "schedule": crontab(minute=0, hour=9),  # Daily at 09:00 UTC
        },
        # DLQ retry - every 4 hours
        "retry-failed-ingestion": {
            "task": "src.worker.retry_failed_ingestion_items",
            "schedule": crontab(minute=0, hour="*/4"),  # Every 4 hours
            "args": (10,),  # Process up to 10 items per run
        },
        # AI analysis retry - every 6 hours
        "retry-failed-ai-analysis": {
            "task": "src.worker.retry_failed_ai_analysis",
            "schedule": crontab(minute=30, hour="*/6"),  # Every 6 hours at :30
            "args": (10,),  # Process up to 10 items per run
        },
    },
)

# Register tasks declared under src.tasks (used by beat_schedule entries with "tasks.*").
# We keep this import local to avoid circular import issues until celery_app is defined.
try:  # pragma: no cover - defensive; task modules may be optional in some deploys
    import src.tasks  # noqa: F401
except Exception as exc:
    logger.warning("Failed to import src.tasks for Celery registration: %s", exc)


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=300,  # 5 minutes
    autoretry_for=(Exception,),
    retry_backoff=True,
    time_limit=3600,  # 1 hour hard limit
    soft_time_limit=3000,  # 50 min soft limit (allows graceful shutdown)
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


@celery_app.task(
    time_limit=1800,  # 30 min hard limit
    soft_time_limit=1500,  # 25 min soft limit
)
def run_content_backfill():
    """Scheduled task to backfill document content and obligations."""
    from src.ingestion.backfill import ContentBackfillService

    logger.info("Starting scheduled content backfill task via Celery")
    db = SessionLocal()
    try:
        service = ContentBackfillService(db)
        result = service.backfill_batch(limit=50, analyze=True)
        logger.info(
            "Content backfill completed: "
            f"{result.get('filled', 0)}/{result.get('processed', 0)} filled, "
            f"{result.get('errors', 0)} errors"
        )
        return result
    except Exception as exc:
        logger.error(f"Content backfill failed: {exc}")
        raise
    finally:
        db.close()


@celery_app.task(
    time_limit=3600,  # 1 hour hard limit
    soft_time_limit=3000,  # 50 min soft limit
)
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


@celery_app.task(
    time_limit=600,  # 10 min hard limit per document
    soft_time_limit=540,  # 9 min soft limit
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=True,
)
def index_document_rag(doc_id: int):
    """
    Background task to index document chunks for RAG retrieval.

    This task runs asynchronously after document ingestion to avoid
    blocking the main ingestion pipeline with slow embedding operations.

    Args:
        doc_id: Database ID of the document to index

    Returns:
        Dict with indexing results

    Example:
        index_document_rag.delay(123)
    """
    from src.models import LegalDocument
    from src.ai.rag_indexer import RAGIndexer

    logger.info(f"Starting RAG indexing for document ID: {doc_id}")
    db = SessionLocal()

    try:
        doc = db.query(LegalDocument).filter(LegalDocument.id == doc_id).first()
        if not doc:
            logger.warning(f"Document {doc_id} not found for RAG indexing")
            return {"status": "not_found", "doc_id": doc_id}

        if not doc.full_text:
            logger.info(f"Document {doc_id} has no full_text, skipping RAG indexing")
            return {"status": "skipped", "doc_id": doc_id, "reason": "no_content"}

        rag_indexer = RAGIndexer(db)
        rag_indexer.index_document(doc)

        logger.info(f"RAG indexing completed for document {doc_id} ({doc.celex})")
        return {
            "status": "completed",
            "doc_id": doc_id,
            "celex": doc.celex,
        }

    except Exception as e:
        logger.error(f"RAG indexing failed for document {doc_id}: {e}")
        raise

    finally:
        db.close()


@celery_app.task(
    time_limit=1800,  # 30 min hard limit
    soft_time_limit=1500,  # 25 min soft limit
)
def retry_failed_ingestion_items(limit: int = 10):
    """
    Retry failed ingestion items from the Dead Letter Queue.

    Args:
        limit: Maximum number of items to retry

    Returns:
        Dict with retry results
    """
    from src.models.compliance_workflow import FailedIngestionItem
    from src.ingestion.processor import IngestionProcessor
    from src.utils.time import utc_now

    logger.info(f"Starting DLQ retry task, limit={limit}")
    db = SessionLocal()

    try:
        # Find items ready for retry
        items = db.query(FailedIngestionItem).filter(
            FailedIngestionItem.status == "pending",
            FailedIngestionItem.retry_count < FailedIngestionItem.max_retries,
        ).order_by(FailedIngestionItem.created_at.asc()).limit(limit).all()

        if not items:
            logger.info("No failed items to retry")
            return {"status": "completed", "retried": 0, "succeeded": 0, "failed": 0}

        processor = IngestionProcessor(db)
        retried = 0
        succeeded = 0
        failed = 0

        for item in items:
            retried += 1
            item.retry_count += 1
            item.last_retry_at = utc_now()
            item.status = "retrying"
            db.commit()

            try:
                import json
                entry = json.loads(item.entry_json) if item.entry_json else {}
                result = processor.process_entry(entry)

                if result in ("new", "updated"):
                    item.status = "resolved"
                    succeeded += 1
                    logger.info(f"Successfully retried item {item.id} ({item.celex})")
                else:
                    item.status = "pending" if item.retry_count < item.max_retries else "exhausted"
                    failed += 1

            except Exception as e:
                item.error_message = str(e)
                item.status = "pending" if item.retry_count < item.max_retries else "exhausted"
                failed += 1
                logger.warning(f"Retry failed for item {item.id}: {e}")

            db.commit()

        logger.info(f"DLQ retry completed: {retried} retried, {succeeded} succeeded, {failed} failed")
        return {
            "status": "completed",
            "retried": retried,
            "succeeded": succeeded,
            "failed": failed,
        }

    except Exception as e:
        logger.error(f"DLQ retry task failed: {e}")
        raise

    finally:
        db.close()


@celery_app.task(
    time_limit=300,  # 5 min hard limit
    soft_time_limit=240,  # 4 min soft limit
)
def check_obligation_deadlines():
    """
    Check for obligations with approaching deadlines and send alerts.

    Checks for deadlines at 30, 14, and 7 days out, plus overdue items.
    Sends email notifications and creates WebSocket events.

    Returns:
        Dict with alert results
    """
    from datetime import timedelta
    from src.models.compliance_workflow import RegulatoryObligation
    from src.models.models import LegalDocument
    from src.utils.time import utc_now
    from src.email_service import send_email
    from src.config import settings

    logger.info("Starting obligation deadline check")
    db = SessionLocal()

    try:
        now = utc_now()
        alerts_sent = {
            "overdue": 0,
            "7_days": 0,
            "14_days": 0,
            "30_days": 0,
        }

        # Define deadline windows
        windows = [
            ("overdue", now, None),  # Past due
            ("7_days", now, now + timedelta(days=7)),
            ("14_days", now + timedelta(days=7), now + timedelta(days=14)),
            ("30_days", now + timedelta(days=14), now + timedelta(days=30)),
        ]

        all_alerts = []

        for window_name, start, end in windows:
            query = db.query(RegulatoryObligation).join(
                LegalDocument, RegulatoryObligation.doc_id == LegalDocument.id
            ).filter(
                RegulatoryObligation.status.in_(["draft", "in_review", "approved"]),
                RegulatoryObligation.effective_date.isnot(None),
            )

            if window_name == "overdue":
                query = query.filter(RegulatoryObligation.effective_date < start)
            else:
                query = query.filter(
                    RegulatoryObligation.effective_date >= start,
                    RegulatoryObligation.effective_date < end,
                )

            obligations = query.all()

            for obl in obligations:
                doc = db.query(LegalDocument).filter(LegalDocument.id == obl.doc_id).first()
                all_alerts.append({
                    "window": window_name,
                    "obligation_id": obl.obligation_id,
                    "obligation_text": (obl.obligation_text or "")[:200],
                    "article_ref": obl.article_ref,
                    "deadline": obl.effective_date.isoformat() if obl.effective_date else None,
                    "document_title": doc.title if doc else "Unknown",
                    "celex": doc.celex if doc else obl.celex,
                    "status": obl.status,
                })
                alerts_sent[window_name] += 1

        # Send consolidated email if there are alerts
        total_alerts = sum(alerts_sent.values())
        if total_alerts > 0 and settings.ADMIN_EMAIL:
            _send_deadline_alert_email(all_alerts, alerts_sent, settings.ADMIN_EMAIL)

        logger.info(f"Deadline check completed: {alerts_sent}")
        return {
            "status": "completed",
            "alerts": alerts_sent,
            "total": total_alerts,
        }

    except Exception as e:
        logger.error(f"Deadline check failed: {e}")
        raise

    finally:
        db.close()


def _send_deadline_alert_email(alerts: list, counts: dict, to_email: str) -> bool:
    """Send consolidated deadline alert email."""
    from src.email_service import send_email
    from src.utils.time import utc_now

    overdue_count = counts.get("overdue", 0)
    urgent_count = counts.get("7_days", 0)

    if overdue_count > 0:
        subject = f"🚨 OVERDUE: {overdue_count} obligation(s) past deadline"
        status_emoji = "🚨"
    elif urgent_count > 0:
        subject = f"⚠️ URGENT: {urgent_count} obligation(s) due within 7 days"
        status_emoji = "⚠️"
    else:
        subject = f"📅 Compliance Deadline Report - {sum(counts.values())} upcoming"
        status_emoji = "📅"

    # Build HTML email
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
            .header {{ background: {'#dc3545' if overdue_count > 0 else '#ffc107' if urgent_count > 0 else '#17a2b8'};
                      color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
            .content {{ padding: 20px; background: #f8f9fa; }}
            .stats {{ display: flex; gap: 20px; margin: 20px 0; flex-wrap: wrap; }}
            .stat {{ background: white; padding: 15px; border-radius: 8px; text-align: center; min-width: 100px; }}
            .stat-value {{ font-size: 24px; font-weight: bold; }}
            .stat-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
            .overdue {{ color: #dc3545; }}
            .urgent {{ color: #ffc107; }}
            .upcoming {{ color: #17a2b8; }}
            .obligation {{ background: white; padding: 15px; margin: 10px 0; border-radius: 8px;
                          border-left: 4px solid #007bff; }}
            .obligation.overdue {{ border-left-color: #dc3545; }}
            .obligation.urgent {{ border-left-color: #ffc107; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{status_emoji} Compliance Deadline Alert</h1>
            <p>Report generated at {utc_now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        </div>
        <div class="content">
            <div class="stats">
                <div class="stat">
                    <div class="stat-value overdue">{counts.get('overdue', 0)}</div>
                    <div class="stat-label">Overdue</div>
                </div>
                <div class="stat">
                    <div class="stat-value urgent">{counts.get('7_days', 0)}</div>
                    <div class="stat-label">Due in 7 days</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{counts.get('14_days', 0)}</div>
                    <div class="stat-label">Due in 14 days</div>
                </div>
                <div class="stat">
                    <div class="stat-value upcoming">{counts.get('30_days', 0)}</div>
                    <div class="stat-label">Due in 30 days</div>
                </div>
            </div>

            <h2>Obligation Details</h2>
    """

    # Group alerts by window
    for window in ["overdue", "7_days", "14_days", "30_days"]:
        window_alerts = [a for a in alerts if a["window"] == window]
        if not window_alerts:
            continue

        window_label = {
            "overdue": "🚨 Overdue",
            "7_days": "⚠️ Due within 7 days",
            "14_days": "📅 Due within 14 days",
            "30_days": "📆 Due within 30 days",
        }[window]

        html += f"<h3>{window_label}</h3>"

        for alert in window_alerts[:10]:  # Limit to 10 per category
            css_class = "overdue" if window == "overdue" else "urgent" if window == "7_days" else ""
            html += f"""
            <div class="obligation {css_class}">
                <strong>{alert['obligation_id']}</strong> - {alert['celex'] or 'N/A'}<br>
                <small>Deadline: {alert['deadline'] or 'N/A'} | Status: {alert['status']}</small><br>
                <p>{alert['obligation_text'][:200]}{'...' if len(alert['obligation_text']) > 200 else ''}</p>
                <small>Document: {alert['document_title'][:100]}</small>
            </div>
            """

        if len(window_alerts) > 10:
            html += f"<p><em>... and {len(window_alerts) - 10} more</em></p>"

    html += """
            <hr>
            <p style="color: #666; font-size: 12px;">
                This is an automated compliance alert from Yufeed Sentinel.<br>
                <a href="http://localhost:3000/obligations">View all obligations</a>
            </p>
        </div>
    </body>
    </html>
    """

    return send_email(to_email, subject, html)


@celery_app.task(
    time_limit=1800,  # 30 min hard limit
    soft_time_limit=1500,  # 25 min soft limit
)
def retry_failed_ai_analysis(limit: int = 10):
    """
    Retry AI analysis for documents that failed during ingestion.

    This task specifically handles items where source_key == "ai_analysis",
    re-running the analysis and obligation seeding without re-ingesting the document.

    Args:
        limit: Maximum number of items to retry

    Returns:
        Dict with retry results
    """
    import json
    from src.models.compliance_workflow import FailedIngestionItem
    from src.models import LegalDocument
    from src.ai.analyzer import analyze_document
    from src.services.obligation_service import seed_obligations_for_doc
    from src.compliance.scope import infer_scope_tags
    from src.utils.time import utc_now

    logger.info(f"Starting AI analysis retry task, limit={limit}")
    db = SessionLocal()

    try:
        # Find failed AI analysis items
        items = db.query(FailedIngestionItem).filter(
            FailedIngestionItem.status == "pending",
            FailedIngestionItem.source_key == "ai_analysis",
            FailedIngestionItem.retry_count < FailedIngestionItem.max_retries,
        ).order_by(FailedIngestionItem.created_at.asc()).limit(limit).all()

        if not items:
            logger.info("No failed AI analysis items to retry")
            return {"status": "completed", "retried": 0, "succeeded": 0, "failed": 0}

        retried = 0
        succeeded = 0
        failed = 0

        for item in items:
            retried += 1
            item.retry_count += 1
            item.last_retry_at = utc_now()
            item.status = "retrying"
            db.commit()

            try:
                # Parse the stored entry to get doc_id
                entry_data = json.loads(item.entry_json) if item.entry_json else {}
                doc_id = entry_data.get("doc_id")

                if not doc_id:
                    logger.warning(f"No doc_id in DLQ item {item.id}, marking exhausted")
                    item.status = "exhausted"
                    item.error_message = "Missing doc_id in entry_json"
                    db.commit()
                    failed += 1
                    continue

                # Load the document
                doc = db.query(LegalDocument).filter(LegalDocument.id == doc_id).first()
                if not doc:
                    logger.warning(f"Document {doc_id} not found for DLQ item {item.id}")
                    item.status = "exhausted"
                    item.error_message = f"Document {doc_id} not found"
                    db.commit()
                    failed += 1
                    continue

                # Run AI analysis
                article_breakdown = []
                if doc.article_breakdown and isinstance(doc.article_breakdown, dict):
                    article_breakdown = doc.article_breakdown.get("articles", [])

                analysis_results = analyze_document({
                    "celex": doc.celex,
                    "title": doc.title,
                    "publication_date": doc.publication_date,
                    "full_text": doc.full_text,
                    "article_breakdown": article_breakdown,
                })

                # Update document with analysis results
                doc.compliance_domain = analysis_results.get("compliance_domain")
                doc.risk_level = analysis_results.get("risk_level")
                doc.obligations_json = analysis_results.get("obligations_json")
                doc.implementation_deadline = analysis_results.get("implementation_deadline")
                doc.ai_summary = analysis_results.get("ai_summary")
                doc.analyzed_at = analysis_results.get("analyzed_at")

                # Infer scope tags
                scope_tags = infer_scope_tags(
                    doc.title,
                    doc.full_text,
                    doc.ai_summary,
                    doc.obligations_json,
                )
                if scope_tags:
                    doc.scope_tags = scope_tags

                db.commit()

                # Seed obligations
                seed_obligations_for_doc(db, doc, allow_existing=True)

                # Mark as resolved
                item.status = "resolved"
                item.resolved_at = utc_now()
                item.resolved_doc_id = doc.id
                succeeded += 1
                logger.info(f"Successfully retried AI analysis for {doc.celex} (item {item.id})")

            except Exception as e:
                item.error_message = str(e)
                item.status = "pending" if item.retry_count < item.max_retries else "exhausted"
                failed += 1
                logger.warning(f"AI analysis retry failed for item {item.id}: {e}")

            db.commit()

        logger.info(f"AI analysis retry completed: {retried} retried, {succeeded} succeeded, {failed} failed")
        return {
            "status": "completed",
            "retried": retried,
            "succeeded": succeeded,
            "failed": failed,
        }

    except Exception as e:
        logger.error(f"AI analysis retry task failed: {e}")
        raise

    finally:
        db.close()
