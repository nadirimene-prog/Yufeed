"""
Legacy monitoring rules aliases.

Provides backward-compatible `/api/rules` endpoints and forwards to the
canonical `/api/monitoring-rules` handlers.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from src.database import get_db
from src.schemas.transaction_schemas import MonitoringRuleCreate
from src.tenancy.queries import require_tenant
from src.api import monitoring_rules as monitoring_rules_api

router = APIRouter(prefix="/api/rules", tags=["rules-legacy"])


def _normalize_conditions(conditions):
    if isinstance(conditions, list):
        return {"logic": "AND", "conditions": conditions}
    if isinstance(conditions, dict):
        return conditions
    return {"logic": "AND", "conditions": []}


def _to_monitoring_rule_create(payload: dict) -> MonitoringRuleCreate:
    conditions = _normalize_conditions(
        payload.get("conditions") or payload.get("conditions_json") or {}
    )
    thresholds = payload.get("thresholds") or payload.get("aggregation_json")

    return MonitoringRuleCreate(
        name=payload.get("name", "Legacy Rule"),
        description=payload.get("description"),
        category=payload.get("category"),
        severity=payload.get("severity", "medium"),
        conditions=conditions,
        thresholds=thresholds,
        regulatory_source_id=payload.get("regulatory_source_id"),
        regulation_article=payload.get("regulation_article"),
        regulatory_requirement=payload.get("regulatory_requirement"),
        enabled=payload.get("enabled", True),
    )


@router.post("")
def create_rule_alias(payload: dict, response: Response, db: Session = Depends(get_db)):
    response.headers["X-Deprecated"] = "true"
    create_payload = _to_monitoring_rule_create(payload)
    created = monitoring_rules_api.create_rule(create_payload, db)
    return {
        "rule_id": created.rule_id,
        "name": created.name,
        "description": created.description,
        "category": created.category,
        "severity": created.severity,
        "enabled": created.enabled,
        "conditions_json": created.conditions,
        "aggregation_json": created.thresholds,
    }


@router.get("")
def list_rules_alias(
    response: Response,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    enabled: Optional[bool] = None,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    db: Session = Depends(get_db),
):
    response.headers["X-Deprecated"] = "true"
    return monitoring_rules_api.list_rules(skip, limit, enabled, category, severity, db)


@router.get("/{rule_id}")
def get_rule_alias(
    rule_id: str,
    response: Response,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant),
):
    response.headers["X-Deprecated"] = "true"
    return monitoring_rules_api.get_rule(rule_id, db, tenant_id)
