"""
Alerts API Endpoints
Handles alert management, triage, and resolution.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


import uuid
import logging

from src.database import get_db
from src.auth.dependencies import get_current_user
from src.models.transaction_models import Alert, Transaction, Case
from src.services.finding_service import FindingService
from src.schemas.transaction_schemas import AlertCreate, AlertUpdate, AlertResponse, AlertStatistics
from src.audit.recorders import record_event, record_decision
from src.tenancy.queries import (
    get_tenant_filtered_query,
    set_tenant_on_create,
    ensure_tenant_match,
    require_tenant,
)

try:
    from src.ml.prediction.model_service import alert_triage_model
except Exception as exc:
    logger = logging.getLogger(__name__)
    _ml_error = str(exc)

    class _FallbackAlertTriageModel:
        def predict(self, db: Session, alert: Alert, return_proba: bool = True):
            logger.warning(
                "ML triage disabled, falling back to manual_review", extra={"error": _ml_error}
            )
            return {
                "prediction": "unknown",
                "false_positive_probability": 0.5,
                "true_positive_probability": 0.5,
                "confidence": 0.5,
                "confidence_label": "low",
                "recommendation": "manual_review",
                "threshold_used": 0.5,
                "model_version": "unavailable",
            }

    alert_triage_model = _FallbackAlertTriageModel()

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/alerts",
    tags=["alerts"],
    dependencies=[Depends(get_current_user)],
)


class AlertNoteCreate(BaseModel):
    note: str
    author: Optional[str] = None


# ============================================================================
# ALERT CREATION & MANAGEMENT
# ============================================================================


@router.post("", response_model=AlertResponse, status_code=201)
def create_alert(alert: AlertCreate, db: Session = Depends(get_db)):
    """
    Create a new alert.

    Typically called by the rules engine when a monitoring rule is triggered.
    """
    # Generate unique alert_id
    alert_id = f"ALT-{utc_now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

    # Validate transaction exists if provided
    if alert.transaction_id:
        transaction = db.query(Transaction).filter(Transaction.id == alert.transaction_id).first()
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")

    # Create alert
    alert_payload = alert.dict(exclude={"matched_rules", "rule_id"})
    db_alert = Alert(alert_id=alert_id, matched_rules_data=alert.matched_rules, **alert_payload)

    # Phase 4C: Set tenant context on new alert
    set_tenant_on_create(db_alert)

    db.add(db_alert)
    db.flush()  # Flush to get the alert ID before ML prediction

    # Finding-first: normalize alert into a finding through centralized service.
    try:
        tenant_id = db_alert.tenant_id
        if tenant_id:
            FindingService(db).create_or_update_finding(
                tenant_id=tenant_id,
                finding_type="TX_ALERT",
                fingerprint=f"TX_ALERT:ALERT:{alert_id}",
                severity=(db_alert.severity or "").lower() or None,
                title=db_alert.description or db_alert.alert_type,
                summary=db_alert.description,
                source_refs={
                    "alert_id": alert_id,
                    "alert_pk": db_alert.id,
                    "transaction_pk": db_alert.transaction_id,
                    "user_id": db_alert.user_id,
                },
                explainability={
                    "matched_rules": db_alert.matched_rules_data,
                    "evidence": db_alert.evidence,
                    "regulation_context": db_alert.regulation_context,
                    "related_regulations": db_alert.related_regulations,
                },
            )
    except Exception as exc:
        logger.warning("Failed to upsert finding for alert %s: %s", alert_id, exc)

    # Phase 4B: Task 4.4 - ML Auto-Triage
    try:
        # Get ML prediction for triage
        prediction = alert_triage_model.predict(db, db_alert)

        raw_confidence = prediction.get("confidence", 0)
        try:
            confidence = float(raw_confidence)
        except (TypeError, ValueError):
            # Fall back to probability-style payloads when confidence is not numeric.
            confidence = float(
                prediction.get("true_positive_probability")
                or prediction.get("false_positive_probability")
                or 0
            )

        # Store ML prediction
        db_alert.ml_prediction = prediction["prediction"]
        db_alert.ml_confidence = confidence
        db_alert.ml_model_version = prediction.get("model_version", "unknown")

        # Store feature snapshot for explainability
        if prediction.get("features"):
            db_alert.ml_features_snapshot = prediction.get("features")

        # Auto-triage based on ML confidence
        recommendation = prediction.get("recommendation", "manual_review")

        if recommendation == "auto_close" and confidence > 0.85:
            # High confidence false positive - auto-close
            db_alert.status = "auto_closed"
            db_alert.resolution_status = "false_positive"
            db_alert.resolution_notes = (
                f"Auto-closed by ML model (confidence: {confidence:.2%}). "
                f"Prediction: {prediction['prediction']}"
            )
            db_alert.resolved_by = "ML_AUTO_TRIAGE"
            db_alert.resolved_at = utc_now()
            logger.info(f"Alert {alert_id} auto-closed by ML (confidence: {confidence:.2%})")

        elif recommendation == "low_priority":
            # Medium confidence false positive - reduce priority
            db_alert.priority = 4  # Low priority
            logger.info(
                f"Alert {alert_id} set to low priority by ML (confidence: {confidence:.2%})"
            )

        elif prediction["prediction"] == "true_positive" and confidence > 0.8:
            # High confidence true positive - increase priority
            db_alert.priority = 1  # Highest priority
            logger.info(
                f"Alert {alert_id} set to high priority by ML (confidence: {confidence:.2%})"
            )

    except Exception as e:
        # ML prediction failed - log and continue without ML triage
        logger.error(f"ML prediction failed for alert {alert_id}: {e}", exc_info=True)
        db_alert.ml_prediction = "error"
        db_alert.ml_confidence = None
        db_alert.ml_model_version = "error"

    event_record = record_event(
        db,
        event_type="alert.created",
        entity_type="alert",
        entity_id=alert_id,
        payload={
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "user_id": alert.user_id,
            "transaction_id": alert.transaction_id,
            "ml_prediction": db_alert.ml_prediction,
            "ml_confidence": float(db_alert.ml_confidence) if db_alert.ml_confidence else None,
        },
    )
    record_decision(
        db,
        decision="alert",
        event_id=event_record.event_id,
        evidence=alert.evidence,
    )
    db.commit()
    db.refresh(db_alert)

    return db_alert


@router.get("", response_model=List[AlertResponse])
def list_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    severity: Optional[str] = None,
    alert_type: Optional[str] = None,
    user_id: Optional[str] = None,
    assigned_to: Optional[str] = None,
    sar_filed: Optional[bool] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """
    List alerts with filtering options.

    Supports pagination and multiple filter criteria for alert triage.
    Uses eager loading to prevent N+1 queries when accessing related transactions.
    """
    # Phase 4C: Tenant-filtered query
    query = get_tenant_filtered_query(Alert, db).options(joinedload(Alert.transaction))

    # Apply filters
    if status:
        query = query.filter(Alert.status == status)

    if severity:
        query = query.filter(Alert.severity == severity)

    if alert_type:
        query = query.filter(Alert.alert_type == alert_type)

    if user_id:
        query = query.filter(Alert.user_id == user_id)

    if assigned_to:
        query = query.filter(Alert.assigned_to == assigned_to)

    if sar_filed is not None:
        query = query.filter(Alert.sar_filed == sar_filed)

    if start_date:
        query = query.filter(Alert.created_at >= start_date)

    if end_date:
        query = query.filter(Alert.created_at <= end_date)

    # Order by priority (1=highest) and created_at descending
    query = query.order_by(Alert.priority.asc(), Alert.created_at.desc())

    # Pagination
    alerts = query.offset(skip).limit(limit).all()

    return alerts


@router.get("/pending", response_model=List[AlertResponse])
def list_pending_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Get all pending alerts that need triage.

    Ordered by priority and creation date.
    Uses eager loading to prevent N+1 queries.
    """
    # Phase 4C: Tenant-filtered query
    alerts = (
        get_tenant_filtered_query(Alert, db)
        .options(joinedload(Alert.transaction))
        .filter(Alert.status == "pending")
        .order_by(Alert.priority.asc(), Alert.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return alerts


@router.get("/critical", response_model=List[AlertResponse])
def list_critical_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Get all critical severity alerts.

    Requires immediate attention.
    Uses eager loading to prevent N+1 queries.
    """
    # Phase 4C: Tenant-filtered query
    alerts = (
        get_tenant_filtered_query(Alert, db)
        .options(joinedload(Alert.transaction))
        .filter(Alert.severity == "critical")
        .order_by(Alert.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return alerts


@router.get("/statistics/overview", response_model=AlertStatistics)
def get_alert_statistics(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    """
    Get alert statistics for the monitoring dashboard.
    """
    start_date = utc_now() - timedelta(days=days)

    # Phase 4C: Use tenant-filtered queries for statistics
    # Total alerts
    total_alerts = (
        get_tenant_filtered_query(Alert, db).filter(Alert.created_at >= start_date).count()
    )

    # Alerts by status
    base_query = get_tenant_filtered_query(Alert, db)
    status_results = (
        base_query.with_entities(Alert.status, func.count(Alert.id).label("count"))
        .filter(Alert.created_at >= start_date)
        .group_by(Alert.status)
        .all()
    )

    alerts_by_status = {row.status: row.count for row in status_results}

    # Alerts by severity
    severity_results = (
        get_tenant_filtered_query(Alert, db)
        .with_entities(Alert.severity, func.count(Alert.id).label("count"))
        .filter(Alert.created_at >= start_date)
        .group_by(Alert.severity)
        .all()
    )

    alerts_by_severity = {row.severity: row.count for row in severity_results}

    # Specific status counts
    pending_alerts = alerts_by_status.get("pending", 0)
    in_review_alerts = alerts_by_status.get("in_review", 0)
    resolved_alerts = alerts_by_status.get("resolved", 0)
    false_positives = alerts_by_status.get("false_positive", 0)

    # Critical and high severity
    critical_alerts = (
        get_tenant_filtered_query(Alert, db)
        .filter(and_(Alert.created_at >= start_date, Alert.severity == "critical"))
        .count()
    )

    high_severity_alerts = (
        get_tenant_filtered_query(Alert, db)
        .filter(and_(Alert.created_at >= start_date, Alert.severity == "high"))
        .count()
    )

    # Alerts by type
    type_results = (
        get_tenant_filtered_query(Alert, db)
        .with_entities(Alert.alert_type, func.count(Alert.id).label("count"))
        .filter(Alert.created_at >= start_date)
        .group_by(Alert.alert_type)
        .all()
    )

    alerts_by_type = {row.alert_type: row.count for row in type_results}

    return AlertStatistics(
        total_alerts=total_alerts or 0,
        pending_alerts=pending_alerts,
        in_review_alerts=in_review_alerts,
        resolved_alerts=resolved_alerts,
        false_positives=false_positives,
        critical_alerts=critical_alerts or 0,
        high_severity_alerts=high_severity_alerts or 0,
        alerts_by_type=alerts_by_type,
        alerts_by_status=alerts_by_status,
        by_status=alerts_by_status,
        by_severity=alerts_by_severity,
    )


@router.get("/statistics", response_model=AlertStatistics)
def get_alert_statistics_alias(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    """Alias for statistics overview (backward compatibility)."""
    return get_alert_statistics(days=days, db=db)


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(
    alert_id: str, db: Session = Depends(get_db), tenant_id: str = Depends(require_tenant)
):
    """Get a single alert by ID."""
    # Phase 4C: Tenant-filtered query
    alert = get_tenant_filtered_query(Alert, db).filter(Alert.alert_id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Phase 4C: Ensure tenant match
    ensure_tenant_match(alert, tenant_id)

    return alert


@router.patch("/{alert_id}", response_model=AlertResponse)
def update_alert(
    alert_id: str,
    update_data: AlertUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant),
):
    """
    Update alert fields (status, assignment, resolution, etc.).
    """
    # Phase 4C: Tenant-filtered query
    alert = get_tenant_filtered_query(Alert, db).filter(Alert.alert_id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Phase 4C: Ensure tenant match
    ensure_tenant_match(alert, tenant_id)

    # Update fields
    update_dict = update_data.dict(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(alert, field, value)

    alert.updated_at = utc_now()
    record_event(
        db,
        event_type="alert.updated",
        entity_type="alert",
        entity_id=alert.alert_id,
        payload={"changes": update_dict},
    )
    db.commit()
    db.refresh(alert)

    return alert


@router.post("/{alert_id}/notes", response_model=AlertResponse, status_code=201)
def add_alert_note(
    alert_id: str,
    payload: AlertNoteCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant),
):
    """
    Add an investigation note to an alert.
    """
    alert = get_tenant_filtered_query(Alert, db).filter(Alert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    ensure_tenant_match(alert, tenant_id)

    evidence = alert.evidence or {}
    existing_notes = evidence.get("notes")
    notes = existing_notes if isinstance(existing_notes, list) else []
    notes.append(
        {
            "note": payload.note,
            "author": payload.author,
            "created_at": utc_now().isoformat(),
        }
    )
    evidence["notes"] = notes
    alert.evidence = evidence
    alert.updated_at = utc_now()

    record_event(
        db,
        event_type="alert.note_added",
        entity_type="alert",
        entity_id=alert.alert_id,
        payload={"author": payload.author, "note": payload.note},
    )
    db.commit()
    db.refresh(alert)
    return alert


# ============================================================================
# ALERT WORKFLOW
# ============================================================================


@router.post("/{alert_id}/assign", response_model=AlertResponse)
def assign_alert(
    alert_id: str,
    assigned_to: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant),
):
    """
    Assign an alert to a compliance analyst.
    """
    # Phase 4C: Tenant-filtered query
    alert = get_tenant_filtered_query(Alert, db).filter(Alert.alert_id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Phase 4C: Ensure tenant match
    ensure_tenant_match(alert, tenant_id)

    alert.assigned_to = assigned_to
    alert.status = "in_review"
    alert.updated_at = utc_now()

    record_event(
        db,
        event_type="alert.assigned",
        entity_type="alert",
        entity_id=alert.alert_id,
        payload={"assigned_to": assigned_to},
    )
    db.commit()
    db.refresh(alert)

    return alert


@router.post("/{alert_id}/escalate", response_model=AlertResponse)
def escalate_alert(
    alert_id: str,
    escalation_notes: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant),
):
    """
    Escalate an alert to higher priority/management.
    """
    # Phase 4C: Tenant-filtered query
    alert = get_tenant_filtered_query(Alert, db).filter(Alert.alert_id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Phase 4C: Ensure tenant match
    ensure_tenant_match(alert, tenant_id)

    alert.status = "escalated"
    alert.priority = max(1, alert.priority - 1)  # Increase priority

    if escalation_notes:
        if alert.resolution_notes:
            alert.resolution_notes += f"\n\n[ESCALATED] {escalation_notes}"
        else:
            alert.resolution_notes = f"[ESCALATED] {escalation_notes}"

    alert.updated_at = utc_now()

    record_event(
        db,
        event_type="alert.escalated",
        entity_type="alert",
        entity_id=alert.alert_id,
        payload={"notes": escalation_notes},
    )
    db.commit()
    db.refresh(alert)

    return alert


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(
    alert_id: str,
    resolution_status: str,
    resolution_notes: str,
    resolved_by: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant),
):
    """
    Resolve an alert.

    Resolution status: 'confirmed', 'false_positive', 'no_action_required', etc.
    """
    # Phase 4C: Tenant-filtered query
    alert = get_tenant_filtered_query(Alert, db).filter(Alert.alert_id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Phase 4C: Ensure tenant match
    ensure_tenant_match(alert, tenant_id)

    alert.status = "resolved"
    alert.resolution_status = resolution_status
    alert.resolution_notes = resolution_notes
    alert.resolved_by = resolved_by
    alert.resolved_at = utc_now()
    alert.updated_at = utc_now()

    record_event(
        db,
        event_type="alert.resolved",
        entity_type="alert",
        entity_id=alert.alert_id,
        payload={"resolution_status": resolution_status, "resolved_by": resolved_by},
    )
    record_decision(
        db,
        decision=resolution_status,
        evidence={"notes": resolution_notes},
    )
    db.commit()
    db.refresh(alert)

    return alert


@router.post("/{alert_id}/false-positive", response_model=AlertResponse)
def mark_false_positive(
    alert_id: str,
    notes: str,
    resolved_by: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant),
):
    """
    Mark an alert as a false positive.

    This helps improve rule tuning and reduce noise.
    """
    # Phase 4C: Tenant-filtered query
    alert = get_tenant_filtered_query(Alert, db).filter(Alert.alert_id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Phase 4C: Ensure tenant match
    ensure_tenant_match(alert, tenant_id)

    alert.status = "false_positive"
    alert.resolution_status = "false_positive"
    alert.resolution_notes = notes
    alert.resolved_by = resolved_by
    alert.resolved_at = utc_now()
    alert.updated_at = utc_now()

    record_event(
        db,
        event_type="alert.false_positive",
        entity_type="alert",
        entity_id=alert.alert_id,
        payload={"resolved_by": resolved_by},
    )
    db.commit()
    db.refresh(alert)

    # TODO: Update rule false positive rate
    # TODO: Trigger rule tuning process

    return alert


# ============================================================================
# SAR FILING
# ============================================================================


@router.post("/{alert_id}/file-sar", response_model=AlertResponse)
def file_sar(
    alert_id: str,
    sar_id: str,
    filed_by: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant),
):
    """
    Mark that a Suspicious Activity Report (SAR) has been filed for this alert.
    """
    # Phase 4C: Tenant-filtered query
    alert = get_tenant_filtered_query(Alert, db).filter(Alert.alert_id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Phase 4C: Ensure tenant match
    ensure_tenant_match(alert, tenant_id)

    alert.sar_filed = True
    alert.sar_id = sar_id
    alert.sar_filed_at = utc_now()
    alert.resolved_by = filed_by
    alert.status = "resolved"
    alert.resolution_status = "sar_filed"
    alert.updated_at = utc_now()

    record_event(
        db,
        event_type="alert.sar_filed",
        entity_type="alert",
        entity_id=alert.alert_id,
        payload={"sar_id": sar_id, "filed_by": filed_by},
    )
    record_decision(
        db,
        decision="sar_filed",
        evidence={"sar_id": sar_id},
    )
    db.commit()
    db.refresh(alert)

    return alert


@router.get("/sar/filed", response_model=List[AlertResponse])
def list_sar_filed_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Get all alerts that resulted in SAR filings.

    Uses eager loading to prevent N+1 queries.
    """
    # Phase 4C: Tenant-filtered query
    alerts = (
        get_tenant_filtered_query(Alert, db)
        .options(joinedload(Alert.transaction))
        .filter(Alert.sar_filed == True)
        .order_by(Alert.sar_filed_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return alerts


# ============================================================================
# ALERT ENRICHMENT
# ============================================================================


@router.get("/{alert_id}/transaction", response_model=dict)
def get_alert_transaction(
    alert_id: str, db: Session = Depends(get_db), tenant_id: str = Depends(require_tenant)
):
    """
    Get the transaction associated with this alert.
    """
    # Phase 4C: Tenant-filtered query
    alert = (
        get_tenant_filtered_query(Alert, db)
        .options(joinedload(Alert.transaction))
        .filter(Alert.alert_id == alert_id)
        .first()
    )

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Phase 4C: Ensure tenant match
    ensure_tenant_match(alert, tenant_id)

    if not alert.transaction:
        raise HTTPException(status_code=404, detail="No transaction associated with this alert")

    return {"alert_id": alert.alert_id, "transaction": alert.transaction}


@router.get("/{alert_id}/regulatory-context", response_model=dict)
def get_alert_regulatory_context(
    alert_id: str, db: Session = Depends(get_db), tenant_id: str = Depends(require_tenant)
):
    """
    Get the regulatory context for this alert.

    This is Yufeed's unique innovation: linking alerts to specific regulations.
    """
    # Phase 4C: Tenant-filtered query
    alert = get_tenant_filtered_query(Alert, db).filter(Alert.alert_id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Phase 4C: Ensure tenant match
    ensure_tenant_match(alert, tenant_id)

    # TODO: Fetch actual LegalDocument records
    # For now, return the stored context
    return {
        "alert_id": alert.alert_id,
        "related_regulations": alert.related_regulations or [],
        "regulation_context": alert.regulation_context,
        "alert_type": alert.alert_type,
        "severity": alert.severity,
    }
