"""
Cases Management API
Handles investigation cases, workflows, and compliance case management.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import datetime
import uuid

from src.database import get_db
from src.models.transaction_models import Case, Alert, Transaction
from src.models.models import LegalDocument
from src.schemas.transaction_schemas import (
    CaseCreate, CaseUpdate, CaseResponse
)

router = APIRouter(prefix="/api/cases", tags=["cases"])


# ============================================================================
# CASE CREATION & MANAGEMENT
# ============================================================================

@router.post("/", response_model=CaseResponse, status_code=201)
def create_case(
    case: CaseCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new investigation case.

    Cases are created from:
    - High-priority alerts
    - Multiple related alerts
    - Escalated situations
    - Regulatory investigations
    """
    # Generate case ID
    case_id = f"CASE-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

    # Create case
    db_case = Case(
        case_id=case_id,
        **case.dict()
    )

    db.add(db_case)
    db.commit()
    db.refresh(db_case)

    return db_case


@router.post("/from-alert/{alert_id}", response_model=CaseResponse, status_code=201)
def create_case_from_alert(
    alert_id: str,
    assigned_to: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Create an investigation case from an alert.

    Automatically pulls alert context, transaction details, and regulatory info.
    """
    # Get alert
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Generate case ID
    case_id = f"CASE-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

    # Build case from alert
    title = f"Investigation: {alert.alert_type} - {alert.user_id}"
    description = f"""
Case created from alert {alert.alert_id}.

Alert Type: {alert.alert_type}
Severity: {alert.severity}
Description: {alert.description}

Initial Evidence:
{_format_evidence(alert.evidence)}
"""

    # Create case
    db_case = Case(
        case_id=case_id,
        case_type='investigation',
        subject_type='user',
        subject_id=alert.user_id,
        status='open',
        priority=_map_severity_to_priority(alert.severity),
        title=title,
        description=description,
        assigned_to=assigned_to,
        related_alert_ids=[alert.id] if alert.id else [],
        related_transaction_ids=[alert.transaction_id] if alert.transaction_id else [],
        related_users=[alert.user_id],
        applicable_regulation_ids=alert.related_regulations or [],
        evidence=alert.evidence or {}
    )

    db.add(db_case)

    # Update alert
    alert.status = 'in_review'

    db.commit()
    db.refresh(db_case)

    return db_case


@router.get("/", response_model=List[CaseResponse])
def list_cases(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_to: Optional[str] = None,
    case_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List cases with filtering.

    Supports filtering by status, priority, assignee, and type.
    """
    query = db.query(Case)

    # Apply filters
    if status:
        query = query.filter(Case.status == status)

    if priority:
        query = query.filter(Case.priority == priority)

    if assigned_to:
        query = query.filter(Case.assigned_to == assigned_to)

    if case_type:
        query = query.filter(Case.case_type == case_type)

    # Order by priority and date
    query = query.order_by(
        Case.status.asc(),  # Open cases first
        Case.priority.desc(),
        Case.opened_at.desc()
    )

    cases = query.offset(skip).limit(limit).all()

    return cases


@router.get("/{case_id}", response_model=CaseResponse)
def get_case(
    case_id: str,
    db: Session = Depends(get_db)
):
    """Get a single case by ID."""
    case = db.query(Case).filter(Case.case_id == case_id).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    return case


@router.patch("/{case_id}", response_model=CaseResponse)
def update_case(
    case_id: str,
    update_data: CaseUpdate,
    db: Session = Depends(get_db)
):
    """
    Update case fields.
    """
    case = db.query(Case).filter(Case.case_id == case_id).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Update fields
    update_dict = update_data.dict(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(case, field, value)

    case.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(case)

    return case


# ============================================================================
# CASE WORKFLOW
# ============================================================================

@router.post("/{case_id}/assign")
def assign_case(
    case_id: str,
    assigned_to: str,
    team: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Assign a case to an analyst or team.
    """
    case = db.query(Case).filter(Case.case_id == case_id).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    case.assigned_to = assigned_to

    if team:
        case.team = team

    if case.status == 'open':
        case.status = 'in_progress'

    case.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(case)

    return {
        "case_id": case.case_id,
        "assigned_to": assigned_to,
        "status": case.status
    }


@router.post("/{case_id}/escalate")
def escalate_case(
    case_id: str,
    escalation_notes: str,
    db: Session = Depends(get_db)
):
    """
    Escalate a case to higher priority/management.
    """
    case = db.query(Case).filter(Case.case_id == case_id).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    case.status = 'escalated'

    # Increase priority
    if case.priority == 'medium':
        case.priority = 'high'
    elif case.priority == 'low':
        case.priority = 'medium'

    # Add escalation notes
    if case.summary:
        case.summary += f"\n\n[ESCALATED] {escalation_notes}"
    else:
        case.summary = f"[ESCALATED] {escalation_notes}"

    case.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(case)

    return {
        "case_id": case.case_id,
        "status": "escalated",
        "priority": case.priority
    }


@router.post("/{case_id}/close")
def close_case(
    case_id: str,
    outcome: str,
    outcome_notes: str,
    db: Session = Depends(get_db)
):
    """
    Close a case with outcome.

    Outcomes:
    - sar_filed: SAR was filed with authorities
    - no_action: No suspicious activity found
    - account_closed: Subject account closed
    - escalated: Escalated to law enforcement
    - resolved: Issue resolved
    """
    case = db.query(Case).filter(Case.case_id == case_id).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    case.status = 'closed'
    case.outcome = outcome
    case.outcome_notes = outcome_notes
    case.closed_at = datetime.utcnow()
    case.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(case)

    return {
        "case_id": case.case_id,
        "status": "closed",
        "outcome": outcome,
        "closed_at": case.closed_at
    }


# ============================================================================
# CASE CONTEXT & EVIDENCE
# ============================================================================

@router.get("/{case_id}/alerts", response_model=List)
def get_case_alerts(
    case_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all alerts related to a case.

    Uses eager loading to prevent N+1 queries when accessing transactions.
    """
    case = db.query(Case).filter(Case.case_id == case_id).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if not case.related_alert_ids:
        return []

    alerts = db.query(Alert).options(
        joinedload(Alert.transaction)
    ).filter(
        Alert.id.in_(case.related_alert_ids)
    ).all()

    return alerts


@router.get("/{case_id}/transactions", response_model=List)
def get_case_transactions(
    case_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all transactions related to a case.

    Uses eager loading to prevent N+1 queries when accessing alerts.
    """
    case = db.query(Case).filter(Case.case_id == case_id).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if not case.related_transaction_ids:
        return []

    transactions = db.query(Transaction).options(
        joinedload(Transaction.alerts)
    ).filter(
        Transaction.id.in_(case.related_transaction_ids)
    ).all()

    return transactions


@router.get("/{case_id}/regulations")
def get_case_regulations(
    case_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all regulations applicable to a case.
    """
    case = db.query(Case).filter(Case.case_id == case_id).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if not case.applicable_regulation_ids:
        return []

    regulations = db.query(LegalDocument).filter(
        LegalDocument.id.in_(case.applicable_regulation_ids)
    ).all()

    return [
        {
            "id": reg.id,
            "celex": reg.celex,
            "title": reg.title,
            "document_type": reg.document_type
        }
        for reg in regulations
    ]


@router.post("/{case_id}/add-alert/{alert_id}")
def add_alert_to_case(
    case_id: str,
    alert_id: str,
    db: Session = Depends(get_db)
):
    """
    Add an alert to an existing case.

    Used when new related activity is discovered.
    """
    case = db.query(Case).filter(Case.case_id == case_id).first()
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Add alert ID if not already present
    if not case.related_alert_ids:
        case.related_alert_ids = []

    if alert.id not in case.related_alert_ids:
        case.related_alert_ids.append(alert.id)

    # Add transaction if available
    if alert.transaction_id:
        if not case.related_transaction_ids:
            case.related_transaction_ids = []

        if alert.transaction_id not in case.related_transaction_ids:
            case.related_transaction_ids.append(alert.transaction_id)

    # Add user if not present
    if alert.user_id:
        if not case.related_users:
            case.related_users = []

        if alert.user_id not in case.related_users:
            case.related_users.append(alert.user_id)

    # Update alert status
    alert.status = 'in_review'

    case.updated_at = datetime.utcnow()
    db.commit()

    return {
        "case_id": case.case_id,
        "alert_added": alert.alert_id,
        "total_alerts": len(case.related_alert_ids)
    }


@router.post("/{case_id}/add-evidence")
def add_evidence(
    case_id: str,
    evidence_key: str,
    evidence_value: str,
    db: Session = Depends(get_db)
):
    """
    Add evidence to a case.
    """
    case = db.query(Case).filter(Case.case_id == case_id).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if not case.evidence:
        case.evidence = {}

    case.evidence[evidence_key] = evidence_value
    case.updated_at = datetime.utcnow()

    db.commit()

    return {
        "case_id": case.case_id,
        "evidence_added": evidence_key
    }


# ============================================================================
# CASE STATISTICS
# ============================================================================

@router.get("/statistics/overview")
def get_case_statistics(db: Session = Depends(get_db)):
    """
    Get case management statistics.
    """
    # Total cases
    total_cases = db.query(func.count(Case.id)).scalar() or 0

    # Cases by status
    status_results = db.query(
        Case.status,
        func.count(Case.id).label('count')
    ).group_by(Case.status).all()

    cases_by_status = {row.status: row.count for row in status_results}

    # Cases by priority
    priority_results = db.query(
        Case.priority,
        func.count(Case.id).label('count')
    ).group_by(Case.priority).all()

    cases_by_priority = {row.priority: row.count for row in priority_results}

    # Cases by outcome
    outcome_results = db.query(
        Case.outcome,
        func.count(Case.id).label('count')
    ).filter(
        Case.outcome.isnot(None)
    ).group_by(Case.outcome).all()

    cases_by_outcome = {row.outcome: row.count for row in outcome_results}

    return {
        "total_cases": total_cases,
        "cases_by_status": cases_by_status,
        "cases_by_priority": cases_by_priority,
        "cases_by_outcome": cases_by_outcome,
        "open_cases": cases_by_status.get('open', 0) + cases_by_status.get('in_progress', 0)
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _map_severity_to_priority(severity: str) -> str:
    """Map alert severity to case priority."""
    mapping = {
        'critical': 'critical',
        'high': 'high',
        'medium': 'medium',
        'low': 'low'
    }
    return mapping.get(severity, 'medium')


def _format_evidence(evidence: Optional[dict]) -> str:
    """Format evidence dictionary."""
    if not evidence:
        return "No evidence available"

    formatted = []
    for key, value in evidence.items():
        formatted.append(f"- {key}: {value}")

    return "\n".join(formatted)
