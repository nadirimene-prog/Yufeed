from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from src.database import get_db
from src.auth.dependencies import require_any_role, CurrentUser
from src.models.compliance_workflow import (
    PolicyDocument,
    PolicySection,
    RegulatoryObligation,
    InternalRule,
    InternalRuleMapping,
)
from src.models.transaction_models import MonitoringRule
from src.schemas.compliance_workflow_schemas import (
    PolicyCreate,
    PolicyUpdate,
    PolicySectionCreate,
    PolicySectionUpdate,
    InternalRuleCreate,
    InternalRuleUpdate,
    InternalRuleMappingCreate,
)

router = APIRouter(prefix="/api/compliance", tags=["compliance-workflow"])


def _policy_to_dict(policy: PolicyDocument) -> dict:
    return {
        "id": policy.id,
        "policy_id": policy.policy_id,
        "name": policy.name,
        "owner": policy.owner,
        "status": policy.status,
        "language": policy.language,
        "effective_date": policy.effective_date.isoformat() if policy.effective_date else None,
        "last_reviewed_at": policy.last_reviewed_at.isoformat() if policy.last_reviewed_at else None,
        "source_url": policy.source_url,
        "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
    }


def _section_to_dict(section: PolicySection) -> dict:
    return {
        "id": section.id,
        "policy_id": section.policy_id,
        "section_ref": section.section_ref,
        "title": section.title,
        "status": section.status,
        "version": section.version,
        "updated_at": section.updated_at.isoformat() if section.updated_at else None,
    }


def _internal_rule_to_dict(rule: InternalRule) -> dict:
    return {
        "id": rule.id,
        "internal_rule_id": rule.internal_rule_id,
        "obligation_id": rule.obligation_id,
        "policy_section_id": rule.policy_section_id,
        "name": rule.name,
        "description": rule.description,
        "control_owner": rule.control_owner,
        "status": rule.status,
        "reviewed_by": rule.reviewed_by,
        "approved_by": rule.approved_by,
        "approved_at": rule.approved_at.isoformat() if rule.approved_at else None,
        "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
        "policy_section": _section_to_dict(rule.policy_section) if rule.policy_section else None,
    }


def _mapping_to_dict(mapping: InternalRuleMapping, monitoring_rule: Optional[MonitoringRule]) -> dict:
    return {
        "id": mapping.id,
        "internal_rule_id": mapping.internal_rule_id,
        "monitoring_rule_id": mapping.monitoring_rule_id,
        "mapping_type": mapping.mapping_type,
        "created_at": mapping.created_at.isoformat() if mapping.created_at else None,
        "monitoring_rule": {
            "id": monitoring_rule.id,
            "rule_id": monitoring_rule.rule_id,
            "name": monitoring_rule.name,
            "severity": monitoring_rule.severity,
            "enabled": monitoring_rule.enabled,
        } if monitoring_rule else None,
    }


@router.get("/policies")
def list_policies(
    status: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])),
):
    query = db.query(PolicyDocument)
    if status:
        query = query.filter(PolicyDocument.status == status)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(PolicyDocument.name.ilike(like), PolicyDocument.policy_id.ilike(like))
        )
    total = query.count()
    rows = query.order_by(PolicyDocument.updated_at.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": [_policy_to_dict(row) for row in rows]}


@router.post("/policies")
def create_policy(
    payload: PolicyCreate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    policy_id = payload.policy_id or f"POL-{uuid4().hex[:8].upper()}"
    policy = PolicyDocument(
        policy_id=policy_id,
        name=payload.name,
        owner=payload.owner,
        status=payload.status or "draft",
        language=payload.language or "en",
        effective_date=payload.effective_date,
        source_url=payload.source_url,
        content=payload.content,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return _policy_to_dict(policy)


@router.get("/policies/{policy_id}")
def get_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])),
):
    policy = db.query(PolicyDocument).filter(PolicyDocument.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return _policy_to_dict(policy)


@router.patch("/policies/{policy_id}")
def update_policy(
    policy_id: int,
    payload: PolicyUpdate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    policy = db.query(PolicyDocument).filter(PolicyDocument.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(policy, field, value)

    db.commit()
    db.refresh(policy)
    return _policy_to_dict(policy)


@router.get("/policies/{policy_id}/sections")
def list_policy_sections(
    policy_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])),
):
    sections = db.query(PolicySection).filter(PolicySection.policy_id == policy_id).order_by(
        PolicySection.section_ref.asc().nullslast(),
        PolicySection.updated_at.desc(),
    ).all()
    return {"items": [_section_to_dict(section) for section in sections]}


@router.post("/policies/{policy_id}/sections")
def create_policy_section(
    policy_id: int,
    payload: PolicySectionCreate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    policy = db.query(PolicyDocument).filter(PolicyDocument.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    section = PolicySection(
        policy_id=policy_id,
        section_ref=payload.section_ref,
        title=payload.title,
        content=payload.content,
        status=payload.status or "draft",
        version=payload.version,
    )
    db.add(section)
    db.commit()
    db.refresh(section)
    return _section_to_dict(section)


@router.patch("/policy-sections/{section_id}")
def update_policy_section(
    section_id: int,
    payload: PolicySectionUpdate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    section = db.query(PolicySection).filter(PolicySection.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Policy section not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(section, field, value)
    db.commit()
    db.refresh(section)
    return _section_to_dict(section)


@router.get("/obligations/{obligation_id}/internal-rules")
def list_internal_rules(
    obligation_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])),
):
    rules = db.query(InternalRule).filter(InternalRule.obligation_id == obligation_id).order_by(
        InternalRule.updated_at.desc()
    ).all()

    items = []
    for rule in rules:
        mappings = db.query(InternalRuleMapping, MonitoringRule).outerjoin(
            MonitoringRule, InternalRuleMapping.monitoring_rule_id == MonitoringRule.id
        ).filter(InternalRuleMapping.internal_rule_id == rule.id).all()
        items.append(
            {
                **_internal_rule_to_dict(rule),
                "mappings": [_mapping_to_dict(mapping, monitoring_rule) for mapping, monitoring_rule in mappings],
            }
        )

    return {"items": items}


@router.post("/obligations/{obligation_id}/internal-rules")
def create_internal_rule(
    obligation_id: int,
    payload: InternalRuleCreate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    obligation = db.query(RegulatoryObligation).filter(RegulatoryObligation.id == obligation_id).first()
    if not obligation:
        raise HTTPException(status_code=404, detail="Obligation not found")

    internal_rule_id = payload.internal_rule_id or f"IR-{uuid4().hex[:8].upper()}"
    rule = InternalRule(
        internal_rule_id=internal_rule_id,
        obligation_id=obligation_id,
        policy_section_id=payload.policy_section_id,
        name=payload.name,
        description=payload.description,
        control_owner=payload.control_owner,
        status=payload.status or "draft",
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return _internal_rule_to_dict(rule)


@router.patch("/internal-rules/{internal_rule_id}")
def update_internal_rule(
    internal_rule_id: int,
    payload: InternalRuleUpdate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    rule = db.query(InternalRule).filter(InternalRule.id == internal_rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Internal rule not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return _internal_rule_to_dict(rule)


@router.get("/internal-rules/{internal_rule_id}/mappings")
def list_internal_rule_mappings(
    internal_rule_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])),
):
    mappings = db.query(InternalRuleMapping, MonitoringRule).outerjoin(
        MonitoringRule, InternalRuleMapping.monitoring_rule_id == MonitoringRule.id
    ).filter(InternalRuleMapping.internal_rule_id == internal_rule_id).all()
    return {"items": [_mapping_to_dict(mapping, monitoring_rule) for mapping, monitoring_rule in mappings]}


@router.post("/internal-rules/{internal_rule_id}/mappings")
def create_internal_rule_mapping(
    internal_rule_id: int,
    payload: InternalRuleMappingCreate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    rule = db.query(InternalRule).filter(InternalRule.id == internal_rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Internal rule not found")

    monitoring_rule = None
    monitoring_rule_id = payload.monitoring_rule_id
    if not monitoring_rule_id and payload.monitoring_rule_rule_id:
        monitoring_rule = db.query(MonitoringRule).filter(
            MonitoringRule.rule_id == payload.monitoring_rule_rule_id
        ).first()
        if not monitoring_rule:
            raise HTTPException(status_code=404, detail="Monitoring rule not found")
        monitoring_rule_id = monitoring_rule.id
    elif monitoring_rule_id:
        monitoring_rule = db.query(MonitoringRule).filter(MonitoringRule.id == monitoring_rule_id).first()
        if not monitoring_rule:
            raise HTTPException(status_code=404, detail="Monitoring rule not found")

    mapping = InternalRuleMapping(
        internal_rule_id=internal_rule_id,
        monitoring_rule_id=monitoring_rule_id,
        mapping_type=payload.mapping_type or "transaction_monitoring",
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return _mapping_to_dict(mapping, monitoring_rule)
