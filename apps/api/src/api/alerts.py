"""
Alerts API Endpoints
Handles alert management, triage, and resolution.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

from src.database import get_db
from src.models.transaction_models import Alert, Transaction, Case
from src.schemas.transaction_schemas import (
    AlertCreate, AlertUpdate, AlertResponse,
    AlertStatistics
)
from src.audit.recorders import record_event, record_decision

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


# ============================================================================
# ALERT CREATION & MANAGEMENT
# ============================================================================

@router.post("/", response_model=AlertResponse, status_code=201)
def create_alert(
    alert: AlertCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new alert.

    Typically called by the rules engine when a monitoring rule is triggered.
    """
    # Generate unique alert_id
    alert_id = f"ALT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

    # Validate transaction exists if provided
    if alert.transaction_id:
        transaction = db.query(Transaction).filter(
            Transaction.id == alert.transaction_id
        ).first()
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")

    # Create alert
    db_alert = Alert(
        alert_id=alert_id,
        **alert.dict()
    )

    db.add(db_alert)
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


@router.get("/", response_model=List[AlertResponse])
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
    db: Session = Depends(get_db)
):
    """
    List alerts with filtering options.

    Supports pagination and multiple filter criteria for alert triage.
    Uses eager loading to prevent N+1 queries when accessing related transactions.
    """
    query = db.query(Alert).options(
        joinedload(Alert.transaction)
    )

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
    db: Session = Depends(get_db)
):
    """
    Get all pending alerts that need triage.

    Ordered by priority and creation date.
    Uses eager loading to prevent N+1 queries.
    """
    alerts = db.query(Alert).options(
        joinedload(Alert.transaction)
    ).filter(
        Alert.status == 'pending'
    ).order_by(
        Alert.priority.asc(),
        Alert.created_at.desc()
    ).offset(skip).limit(limit).all()

    return alerts


@router.get("/critical", response_model=List[AlertResponse])
def list_critical_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get all critical severity alerts.

    Requires immediate attention.
    Uses eager loading to prevent N+1 queries.
    """
    alerts = db.query(Alert).options(
        joinedload(Alert.transaction)
    ).filter(
        Alert.severity == 'critical'
    ).order_by(
        Alert.created_at.desc()
    ).offset(skip).limit(limit).all()

    return alerts


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(
    alert_id: str,
    db: Session = Depends(get_db)
):
    """Get a single alert by ID."""
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return alert


@router.patch("/{alert_id}", response_model=AlertResponse)
def update_alert(
    alert_id: str,
    update_data: AlertUpdate,
    db: Session = Depends(get_db)
):
    """
    Update alert fields (status, assignment, resolution, etc.).
    """
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Update fields
    update_dict = update_data.dict(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(alert, field, value)

    alert.updated_at = datetime.utcnow()
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


# ============================================================================
# ALERT WORKFLOW
# ============================================================================

@router.post("/{alert_id}/assign", response_model=AlertResponse)
def assign_alert(
    alert_id: str,
    assigned_to: str,
    db: Session = Depends(get_db)
):
    """
    Assign an alert to a compliance analyst.
    """
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.assigned_to = assigned_to
    alert.status = 'in_review'
    alert.updated_at = datetime.utcnow()

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
    db: Session = Depends(get_db)
):
    """
    Escalate an alert to higher priority/management.
    """
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = 'escalated'
    alert.priority = max(1, alert.priority - 1)  # Increase priority

    if escalation_notes:
        if alert.resolution_notes:
            alert.resolution_notes += f"\n\n[ESCALATED] {escalation_notes}"
        else:
            alert.resolution_notes = f"[ESCALATED] {escalation_notes}"

    alert.updated_at = datetime.utcnow()

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
    db: Session = Depends(get_db)
):
    """
    Resolve an alert.

    Resolution status: 'confirmed', 'false_positive', 'no_action_required', etc.
    """
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = 'resolved'
    alert.resolution_status = resolution_status
    alert.resolution_notes = resolution_notes
    alert.resolved_by = resolved_by
    alert.resolved_at = datetime.utcnow()
    alert.updated_at = datetime.utcnow()

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
    db: Session = Depends(get_db)
):
    """
    Mark an alert as a false positive.

    This helps improve rule tuning and reduce noise.
    """
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = 'false_positive'
    alert.resolution_status = 'false_positive'
    alert.resolution_notes = notes
    alert.resolved_by = resolved_by
    alert.resolved_at = datetime.utcnow()
    alert.updated_at = datetime.utcnow()

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
    db: Session = Depends(get_db)
):
    """
    Mark that a Suspicious Activity Report (SAR) has been filed for this alert.
    """
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.sar_filed = True
    alert.sar_id = sar_id
    alert.sar_filed_at = datetime.utcnow()
    alert.resolved_by = filed_by
    alert.status = 'resolved'
    alert.resolution_status = 'sar_filed'
    alert.updated_at = datetime.utcnow()

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
    db: Session = Depends(get_db)
):
    """
    Get all alerts that resulted in SAR filings.

    Uses eager loading to prevent N+1 queries.
    """
    alerts = db.query(Alert).options(
        joinedload(Alert.transaction)
    ).filter(
        Alert.sar_filed == True
    ).order_by(
        Alert.sar_filed_at.desc()
    ).offset(skip).limit(limit).all()

    return alerts


# ============================================================================
# ALERT STATISTICS
# ============================================================================

@router.get("/statistics/overview", response_model=AlertStatistics)
def get_alert_statistics(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get alert statistics for the monitoring dashboard.
    """
    start_date = datetime.utcnow() - timedelta(days=days)

    # Total alerts
    total_alerts = db.query(func.count(Alert.id)).filter(
        Alert.created_at >= start_date
    ).scalar()

    # Alerts by status
    status_results = db.query(
        Alert.status,
        func.count(Alert.id).label('count')
    ).filter(
        Alert.created_at >= start_date
    ).group_by(Alert.status).all()

    alerts_by_status = {row.status: row.count for row in status_results}

    # Specific status counts
    pending_alerts = alerts_by_status.get('pending', 0)
    in_review_alerts = alerts_by_status.get('in_review', 0)
    resolved_alerts = alerts_by_status.get('resolved', 0)
    false_positives = alerts_by_status.get('false_positive', 0)

    # Critical and high severity
    critical_alerts = db.query(func.count(Alert.id)).filter(
        and_(
            Alert.created_at >= start_date,
            Alert.severity == 'critical'
        )
    ).scalar()

    high_severity_alerts = db.query(func.count(Alert.id)).filter(
        and_(
            Alert.created_at >= start_date,
            Alert.severity == 'high'
        )
    ).scalar()

    # Alerts by type
    type_results = db.query(
        Alert.alert_type,
        func.count(Alert.id).label('count')
    ).filter(
        Alert.created_at >= start_date
    ).group_by(Alert.alert_type).all()

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
        alerts_by_status=alerts_by_status
    )


# ============================================================================
# ALERT ENRICHMENT
# ============================================================================

@router.get("/{alert_id}/transaction", response_model=dict)
def get_alert_transaction(
    alert_id: str,
    db: Session = Depends(get_db)
):
    """
    Get the transaction associated with this alert.
    """
    alert = db.query(Alert).options(
        joinedload(Alert.transaction)
    ).filter(Alert.alert_id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if not alert.transaction:
        raise HTTPException(status_code=404, detail="No transaction associated with this alert")

    return {
        "alert_id": alert.alert_id,
        "transaction": alert.transaction
    }


@router.get("/{alert_id}/regulatory-context", response_model=dict)
def get_alert_regulatory_context(
    alert_id: str,
    db: Session = Depends(get_db)
):
    """
    Get the regulatory context for this alert.

    This is Yufeed's unique innovation: linking alerts to specific regulations.
    """
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # TODO: Fetch actual LegalDocument records
    # For now, return the stored context
    return {
        "alert_id": alert.alert_id,
        "related_regulations": alert.related_regulations or [],
        "regulation_context": alert.regulation_context,
        "alert_type": alert.alert_type,
        "severity": alert.severity
    }
