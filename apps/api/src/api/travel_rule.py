from datetime import datetime
from typing import Dict, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.auth.dependencies import require_any_role, CurrentUser
from src.audit.recorders import record_event
from src.database import get_db
from sqlalchemy.orm import Session

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


_REQUESTS: Dict[str, TravelRuleResponse] = {}


@router.post("/requests", response_model=TravelRuleResponse)
def create_travel_rule_request(
    request: TravelRuleRequest,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "user"]))
):
    request_id = f"TR-{uuid.uuid4().hex[:10].upper()}"
    response = TravelRuleResponse(
        request_id=request_id,
        status="pending",
        created_at=datetime.utcnow(),
        payload=request,
    )

    _REQUESTS[request_id] = response

    record_event(
        db,
        event_type="travel_rule_request",
        entity_type="transaction",
        entity_id=request.transaction_id,
        payload=request.model_dump(),
        metadata={"request_id": request_id, "status": "pending"},
    )

    return response


@router.get("/requests/{request_id}", response_model=TravelRuleResponse)
def get_travel_rule_request(
    request_id: str,
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "auditor"]))
):
    response = _REQUESTS.get(request_id)
    if not response:
        raise HTTPException(status_code=404, detail="Travel rule request not found")
    return response


@router.post("/requests/{request_id}/submit", response_model=TravelRuleResponse)
def submit_travel_rule_request(
    request_id: str,
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "user"]))
):
    response = _REQUESTS.get(request_id)
    if not response:
        raise HTTPException(status_code=404, detail="Travel rule request not found")
    updated = response.copy(update={"status": "submitted"})
    _REQUESTS[request_id] = updated
    return updated
