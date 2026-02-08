from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


from typing import Dict, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.auth.dependencies import require_any_role, CurrentUser
from src.audit.recorders import record_event
from src.database import get_db
from sqlalchemy.orm import Session
from src.models.travel_rule import TravelRuleRequestRecord
from src.audit.models import AuditLog
from src.tenancy.context import get_current_tenant

router = APIRouter(prefix="/api/travel-rule", tags=["travel-rule"])


class Party(BaseModel):
    name: str
    account_id: Optional[str] = None
    wallet_address: Optional[str] = None
    country: Optional[str] = None


class TravelRuleRequest(BaseModel):
    transaction_id: str
    amount: float
    currency: str = Field(..., min_length=2, max_length=8)
    asset: Optional[str] = None
    originator: Party
    beneficiary: Party
    message: Optional[str] = None


class TravelRuleResponse(BaseModel):
    request_id: str
    status: str
    created_at: datetime
    payload: TravelRuleRequest


@router.post("/requests", response_model=TravelRuleResponse)
def create_travel_rule_request(
    request: TravelRuleRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "user"])
    ),
):
    tenant_id = current_user.tenant_id or get_current_tenant()
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Tenant context is required")

    request_id = f"TR-{uuid.uuid4().hex[:10].upper()}"
    response = TravelRuleResponse(
        request_id=request_id,
        status="pending",
        created_at=utc_now(),
        payload=request,
    )

    db_request = TravelRuleRequestRecord(
        request_id=request_id,
        transaction_id=request.transaction_id,
        amount=str(request.amount),
        currency=request.currency,
        asset=request.asset,
        originator=request.originator.model_dump(),
        beneficiary=request.beneficiary.model_dump(),
        message=request.message,
        status="pending",
    )
    db.add(db_request)
    db.commit()

    record_event(
        db,
        tenant_id=tenant_id,
        event_type="travel_rule_request",
        entity_type="transaction",
        entity_id=request.transaction_id,
        payload=request.model_dump(),
        metadata={"request_id": request_id, "status": "pending"},
    )

    audit_entry = AuditLog(
        audit_id=uuid.uuid4().hex,
        tenant_id=tenant_id,
        actor_id=current_user.user_id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        actor_type="user",
        action="create",
        method="POST",
        path="/api/travel-rule/requests",
        entity_type="travel_rule_request",
        entity_id=request_id,
        status_code=200,
        changes={"status": "pending", "transaction_id": request.transaction_id},
    )
    db.add(audit_entry)
    db.commit()

    return response


@router.get("/requests", response_model=list[TravelRuleResponse])
def list_travel_rule_requests(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])
    ),
):
    query = db.query(TravelRuleRequestRecord)
    if status:
        query = query.filter(TravelRuleRequestRecord.status == status)
    rows = query.order_by(TravelRuleRequestRecord.created_at.desc()).all()
    responses = []
    for row in rows:
        responses.append(
            TravelRuleResponse(
                request_id=row.request_id,
                status=row.status,
                created_at=row.created_at,
                payload=TravelRuleRequest(
                    transaction_id=row.transaction_id,
                    amount=float(row.amount),
                    currency=row.currency,
                    asset=row.asset,
                    originator=Party(**(row.originator or {})),
                    beneficiary=Party(**(row.beneficiary or {})),
                    message=row.message,
                ),
            )
        )
    return responses


@router.get("/requests/{request_id}", response_model=TravelRuleResponse)
def get_travel_rule_request(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "auditor"])
    ),
):
    row = (
        db.query(TravelRuleRequestRecord)
        .filter(TravelRuleRequestRecord.request_id == request_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Travel rule request not found")
    return TravelRuleResponse(
        request_id=row.request_id,
        status=row.status,
        created_at=row.created_at,
        payload=TravelRuleRequest(
            transaction_id=row.transaction_id,
            amount=float(row.amount),
            currency=row.currency,
            asset=row.asset,
            originator=Party(**(row.originator or {})),
            beneficiary=Party(**(row.beneficiary or {})),
            message=row.message,
        ),
    )


@router.post("/requests/{request_id}/submit", response_model=TravelRuleResponse)
def submit_travel_rule_request(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "user"])
    ),
):
    tenant_id = current_user.tenant_id or get_current_tenant()
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Tenant context is required")

    row = (
        db.query(TravelRuleRequestRecord)
        .filter(TravelRuleRequestRecord.request_id == request_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Travel rule request not found")
    row.status = "submitted"
    row.submitted_at = utc_now()
    db.commit()
    db.refresh(row)

    audit_entry = AuditLog(
        audit_id=uuid.uuid4().hex,
        tenant_id=tenant_id,
        actor_id=current_user.user_id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        actor_type="user",
        action="submit",
        method="POST",
        path=f"/api/travel-rule/requests/{request_id}/submit",
        entity_type="travel_rule_request",
        entity_id=request_id,
        status_code=200,
        changes={"status": "submitted"},
    )
    db.add(audit_entry)
    db.commit()
    return TravelRuleResponse(
        request_id=row.request_id,
        status=row.status,
        created_at=row.created_at,
        payload=TravelRuleRequest(
            transaction_id=row.transaction_id,
            amount=float(row.amount),
            currency=row.currency,
            asset=row.asset,
            originator=Party(**(row.originator or {})),
            beneficiary=Party(**(row.beneficiary or {})),
            message=row.message,
        ),
    )
