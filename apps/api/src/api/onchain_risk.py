from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.auth.dependencies import require_any_role, CurrentUser
from src.plugins.registry import get_plugin, list_plugins, register_plugin
from src.plugins.onchain import get_default_onchain_plugin
from src.audit.recorders import record_event
from src.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/onchain", tags=["onchain-risk"])


class AddressRiskRequest(BaseModel):
    address: str = Field(..., min_length=4)
    chain: Optional[str] = None
    asset: Optional[str] = None


class AddressRiskResponse(BaseModel):
    address: str
    risk_score: float
    risk_level: str
    vendor: str
    signals: Dict[str, Any]


@router.get("/plugins")
def get_plugins(_: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "user"]))):
    if not list_plugins():
        register_plugin("mock-onchain", get_default_onchain_plugin())
    return {"plugins": list_plugins()}


@router.post("/score", response_model=AddressRiskResponse)
async def score_address(
    request: AddressRiskRequest,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "user"]))
):
    plugin = get_plugin("mock-onchain")
    if not plugin:
        plugin = get_default_onchain_plugin()
        register_plugin("mock-onchain", plugin)

    result = await plugin.score_address(request.address)

    record_event(
        db,
        event_type="onchain_risk_check",
        entity_type="wallet_address",
        entity_id=request.address,
        payload={
            "chain": request.chain,
            "asset": request.asset,
        },
        metadata={
            "vendor": result.get("vendor"),
            "risk_score": result.get("risk_score"),
        },
    )

    return AddressRiskResponse(**result)
