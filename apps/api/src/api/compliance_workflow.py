import re
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
from src.models.models import LegalDocument
from src.schemas.compliance_workflow_schemas import (
    PolicyCreate,
    PolicyUpdate,
    PolicySectionCreate,
    PolicySectionUpdate,
    InternalRuleCreate,
    InternalRuleUpdate,
    InternalRuleMappingCreate,
)
from src.tenancy.context import get_current_tenant
from src.utils.time import utc_now

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
        "last_reviewed_at": (
            policy.last_reviewed_at.isoformat() if policy.last_reviewed_at else None
        ),
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


def _mapping_to_dict(
    mapping: InternalRuleMapping, monitoring_rule: Optional[MonitoringRule]
) -> dict:
    return {
        "id": mapping.id,
        "internal_rule_id": mapping.internal_rule_id,
        "monitoring_rule_id": mapping.monitoring_rule_id,
        "mapping_type": mapping.mapping_type,
        "created_at": mapping.created_at.isoformat() if mapping.created_at else None,
        "monitoring_rule": (
            {
                "id": monitoring_rule.id,
                "rule_id": monitoring_rule.rule_id,
                "name": monitoring_rule.name,
                "severity": monitoring_rule.severity,
                "enabled": monitoring_rule.enabled,
            }
            if monitoring_rule
            else None
        ),
    }


def _current_tenant_id(current_user: Optional[CurrentUser]) -> str:
    tenant_id = get_current_tenant()
    if tenant_id:
        return tenant_id
    if current_user and current_user.tenant_id:
        return current_user.tenant_id
    return "default"


def _policy_tenant_id(policy: PolicyDocument) -> Optional[str]:
    metadata = policy.metadata_json
    if isinstance(metadata, dict):
        tenant_id = metadata.get("tenant_id")
        if isinstance(tenant_id, str) and tenant_id:
            return tenant_id
    return None


def _policy_visible_to_tenant(policy: PolicyDocument, tenant_id: str) -> bool:
    policy_tenant = _policy_tenant_id(policy)
    return policy_tenant in (None, tenant_id)


def _resolve_policy(db: Session, policy_identifier: str | int) -> Optional[PolicyDocument]:
    policy_key = str(policy_identifier)
    policy = db.query(PolicyDocument).filter(PolicyDocument.policy_id == policy_key).first()
    if policy:
        return policy

    if policy_key.isdigit():
        return db.query(PolicyDocument).filter(PolicyDocument.id == int(policy_key)).first()

    return None


def _resolve_obligation(
    db: Session, obligation_identifier: str | int
) -> Optional[RegulatoryObligation]:
    obligation_key = str(obligation_identifier)
    obligation = (
        db.query(RegulatoryObligation)
        .filter(RegulatoryObligation.obligation_id == obligation_key)
        .first()
    )
    if obligation:
        return obligation

    if obligation_key.isdigit():
        return (
            db.query(RegulatoryObligation)
            .filter(RegulatoryObligation.id == int(obligation_key))
            .first()
        )

    return None


def _resolve_internal_rule(
    db: Session, internal_rule_identifier: str | int
) -> Optional[InternalRule]:
    internal_rule_key = str(internal_rule_identifier)
    rule = db.query(InternalRule).filter(InternalRule.internal_rule_id == internal_rule_key).first()
    if rule:
        return rule

    if internal_rule_key.isdigit():
        return db.query(InternalRule).filter(InternalRule.id == int(internal_rule_key)).first()

    return None


def _obligation_visible_to_tenant(
    db: Session, obligation: RegulatoryObligation, tenant_id: str
) -> bool:
    if not obligation.linked_policy_id:
        return True

    linked_policy = (
        db.query(PolicyDocument).filter(PolicyDocument.id == obligation.linked_policy_id).first()
    )
    if not linked_policy:
        return True
    return _policy_visible_to_tenant(linked_policy, tenant_id)


def _internal_rule_visible_to_tenant(db: Session, rule: InternalRule, tenant_id: str) -> bool:
    obligation = (
        db.query(RegulatoryObligation).filter(RegulatoryObligation.id == rule.obligation_id).first()
    )
    if not obligation:
        return True
    return _obligation_visible_to_tenant(db, obligation, tenant_id)


def _serialize_obligation(obligation: RegulatoryObligation) -> dict:
    return {
        "id": obligation.id,
        "obligation_id": obligation.obligation_id,
        "status": obligation.status,
        "article_ref": obligation.article_ref,
        "obligation_text": obligation.obligation_text,
        "applicability": obligation.applicability,
        "effective_date": (
            obligation.effective_date.isoformat() if obligation.effective_date else None
        ),
        "linked_policy_id": obligation.linked_policy_id,
        "approved_by": obligation.approved_by,
        "approved_at": obligation.approved_at.isoformat() if obligation.approved_at else None,
        "review_notes": obligation.review_notes,
        "updated_at": obligation.updated_at.isoformat() if obligation.updated_at else None,
    }


def _extract_obligation_candidates(policy_content: Optional[str], policy_name: str) -> list[str]:
    if policy_content:
        segments = [s.strip() for s in re.split(r"[\n\.]+", policy_content) if s.strip()]
        candidates: list[str] = []
        seen: set[str] = set()
        for segment in segments:
            if len(segment) < 20:
                continue
            if segment in seen:
                continue
            seen.add(segment)
            candidates.append(segment)
        if candidates:
            return candidates[:10]

    return [
        f"Implement and monitor controls required by policy '{policy_name}'.",
        f"Document and evidence compliance with policy '{policy_name}'.",
    ]


@router.get("/policies")
def list_policies(
    status: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])
    ),
):
    tenant_id = _current_tenant_id(current_user)
    query = db.query(PolicyDocument)
    if status:
        query = query.filter(PolicyDocument.status == status)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(PolicyDocument.name.ilike(like), PolicyDocument.policy_id.ilike(like))
        )
    rows = query.order_by(PolicyDocument.updated_at.desc()).all()
    rows = [row for row in rows if _policy_visible_to_tenant(row, tenant_id)]
    total = len(rows)
    rows = rows[skip : skip + limit]
    return {"total": total, "items": [_policy_to_dict(row) for row in rows]}


@router.post("/policies", status_code=201)
def create_policy(
    payload: PolicyCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    policy_id = payload.policy_id or f"POL-{uuid4().hex[:8].upper()}"
    tenant_id = _current_tenant_id(current_user)
    policy = PolicyDocument(
        policy_id=policy_id,
        name=payload.name,
        owner=payload.owner,
        status=payload.status or "draft",
        language=payload.language or "en",
        effective_date=payload.effective_date,
        source_url=payload.source_url,
        content=payload.content,
        metadata_json={"tenant_id": tenant_id},
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return _policy_to_dict(policy)


@router.post("/policies/{policy_id}/extract-obligations", status_code=201)
def extract_policy_obligations(
    policy_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    tenant_id = _current_tenant_id(current_user)
    policy = _resolve_policy(db, policy_id)
    if not policy or not _policy_visible_to_tenant(policy, tenant_id):
        raise HTTPException(status_code=404, detail="Policy not found")

    synthetic_celex = f"POLICY-{policy.policy_id}"
    document = db.query(LegalDocument).filter(LegalDocument.celex == synthetic_celex).first()
    if not document:
        document = LegalDocument(
            celex=synthetic_celex,
            title=policy.name,
            type="other",
            publication_date=utc_now(),
            full_text=policy.content,
        )
        db.add(document)
        db.flush()
    elif policy.content and not document.full_text:
        document.full_text = policy.content

    created_count = 0
    candidates = _extract_obligation_candidates(policy.content, policy.name)
    for idx, obligation_text in enumerate(candidates, start=1):
        obligation_identifier = f"{policy.policy_id}-OBL-{idx:03d}"
        existing = (
            db.query(RegulatoryObligation)
            .filter(RegulatoryObligation.obligation_id == obligation_identifier)
            .first()
        )
        if existing:
            if existing.linked_policy_id is None:
                existing.linked_policy_id = policy.id
            continue

        obligation = RegulatoryObligation(
            obligation_id=obligation_identifier,
            doc_id=document.id,
            linked_policy_id=policy.id,
            celex=document.celex,
            article_ref=f"Policy Section {idx}",
            obligation_text=obligation_text,
            applicability="all applicable business lines",
            status="draft",
            created_by=current_user.email,
        )
        db.add(obligation)
        created_count += 1

    db.commit()
    return {
        "policy_id": policy.policy_id,
        "status": "completed",
        "created_obligations": created_count,
        "total_candidates": len(candidates),
    }


@router.get("/policies/{policy_id}/obligations")
def list_policy_obligations(
    policy_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])
    ),
):
    tenant_id = _current_tenant_id(current_user)
    policy = _resolve_policy(db, policy_id)
    if not policy or not _policy_visible_to_tenant(policy, tenant_id):
        raise HTTPException(status_code=404, detail="Policy not found")

    obligations = (
        db.query(RegulatoryObligation)
        .filter(RegulatoryObligation.linked_policy_id == policy.id)
        .order_by(RegulatoryObligation.created_at.asc(), RegulatoryObligation.id.asc())
        .all()
    )
    return [_serialize_obligation(obligation) for obligation in obligations]


@router.get("/policies/{policy_id}")
def get_policy(
    policy_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])
    ),
):
    tenant_id = _current_tenant_id(current_user)
    policy = _resolve_policy(db, policy_id)
    if not policy or not _policy_visible_to_tenant(policy, tenant_id):
        raise HTTPException(status_code=404, detail="Policy not found")
    return _policy_to_dict(policy)


@router.post("/obligations/{obligation_id}/approve")
def approve_obligation(
    obligation_id: str,
    payload: Optional[dict] = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    tenant_id = _current_tenant_id(current_user)
    obligation = _resolve_obligation(db, obligation_id)
    if not obligation or not _obligation_visible_to_tenant(db, obligation, tenant_id):
        raise HTTPException(status_code=404, detail="Obligation not found")

    obligation.status = "approved"
    obligation.reviewed_by = current_user.email
    obligation.approved_by = current_user.email
    obligation.approved_at = utc_now()
    obligation.updated_at = utc_now()

    if payload and isinstance(payload, dict):
        reviewer_notes = payload.get("reviewer_notes") or payload.get("review_notes")
        if reviewer_notes:
            obligation.review_notes = reviewer_notes

    db.commit()
    db.refresh(obligation)
    return _serialize_obligation(obligation)


@router.patch("/policies/{policy_id}")
def update_policy(
    policy_id: str,
    payload: PolicyUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    tenant_id = _current_tenant_id(current_user)
    policy = _resolve_policy(db, policy_id)
    if not policy or not _policy_visible_to_tenant(policy, tenant_id):
        raise HTTPException(status_code=404, detail="Policy not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(policy, field, value)

    db.commit()
    db.refresh(policy)
    return _policy_to_dict(policy)


@router.get("/policies/{policy_id}/sections")
def list_policy_sections(
    policy_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])
    ),
):
    tenant_id = _current_tenant_id(current_user)
    policy = _resolve_policy(db, policy_id)
    if not policy or not _policy_visible_to_tenant(policy, tenant_id):
        raise HTTPException(status_code=404, detail="Policy not found")

    sections = (
        db.query(PolicySection)
        .filter(PolicySection.policy_id == policy.id)
        .order_by(
            PolicySection.section_ref.asc().nullslast(),
            PolicySection.updated_at.desc(),
        )
        .all()
    )
    return {"items": [_section_to_dict(section) for section in sections]}


@router.post("/policies/{policy_id}/sections", status_code=201)
def create_policy_section(
    policy_id: str,
    payload: PolicySectionCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    tenant_id = _current_tenant_id(current_user)
    policy = _resolve_policy(db, policy_id)
    if not policy or not _policy_visible_to_tenant(policy, tenant_id):
        raise HTTPException(status_code=404, detail="Policy not found")

    section = PolicySection(
        policy_id=policy.id,
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
    obligation_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])
    ),
):
    tenant_id = _current_tenant_id(current_user)
    obligation = _resolve_obligation(db, obligation_id)
    if not obligation or not _obligation_visible_to_tenant(db, obligation, tenant_id):
        raise HTTPException(status_code=404, detail="Obligation not found")

    rules = (
        db.query(InternalRule)
        .filter(InternalRule.obligation_id == obligation.id)
        .order_by(InternalRule.updated_at.desc())
        .all()
    )

    items = []
    for rule in rules:
        mappings = (
            db.query(InternalRuleMapping, MonitoringRule)
            .outerjoin(MonitoringRule, InternalRuleMapping.monitoring_rule_id == MonitoringRule.id)
            .filter(InternalRuleMapping.internal_rule_id == rule.id)
            .all()
        )
        items.append(
            {
                **_internal_rule_to_dict(rule),
                "mappings": [
                    _mapping_to_dict(mapping, monitoring_rule)
                    for mapping, monitoring_rule in mappings
                ],
            }
        )

    return {"items": items}


@router.post("/obligations/{obligation_id}/internal-rules", status_code=201)
def create_internal_rule(
    obligation_id: str,
    payload: InternalRuleCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    tenant_id = _current_tenant_id(current_user)
    obligation = _resolve_obligation(db, obligation_id)
    if not obligation or not _obligation_visible_to_tenant(db, obligation, tenant_id):
        raise HTTPException(status_code=404, detail="Obligation not found")

    internal_rule_id = payload.internal_rule_id or f"IR-{uuid4().hex[:8].upper()}"
    rule = InternalRule(
        internal_rule_id=internal_rule_id,
        obligation_id=obligation.id,
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
    internal_rule_id: str,
    payload: InternalRuleUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    tenant_id = _current_tenant_id(current_user)
    rule = _resolve_internal_rule(db, internal_rule_id)
    if not rule or not _internal_rule_visible_to_tenant(db, rule, tenant_id):
        raise HTTPException(status_code=404, detail="Internal rule not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return _internal_rule_to_dict(rule)


@router.get("/internal-rules/{internal_rule_id}/mappings")
def list_internal_rule_mappings(
    internal_rule_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])
    ),
):
    tenant_id = _current_tenant_id(current_user)
    rule = _resolve_internal_rule(db, internal_rule_id)
    if not rule or not _internal_rule_visible_to_tenant(db, rule, tenant_id):
        raise HTTPException(status_code=404, detail="Internal rule not found")

    mappings = (
        db.query(InternalRuleMapping, MonitoringRule)
        .outerjoin(MonitoringRule, InternalRuleMapping.monitoring_rule_id == MonitoringRule.id)
        .filter(InternalRuleMapping.internal_rule_id == rule.id)
        .all()
    )
    return {
        "items": [
            _mapping_to_dict(mapping, monitoring_rule) for mapping, monitoring_rule in mappings
        ]
    }


@router.post("/internal-rules/{internal_rule_id}/mappings", status_code=201)
def create_internal_rule_mapping(
    internal_rule_id: str,
    payload: InternalRuleMappingCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    tenant_id = _current_tenant_id(current_user)
    rule = _resolve_internal_rule(db, internal_rule_id)
    if not rule or not _internal_rule_visible_to_tenant(db, rule, tenant_id):
        raise HTTPException(status_code=404, detail="Internal rule not found")

    monitoring_rule = None
    monitoring_rule_id = payload.monitoring_rule_id
    if not monitoring_rule_id and payload.monitoring_rule_rule_id:
        monitoring_rule = (
            db.query(MonitoringRule)
            .filter(MonitoringRule.rule_id == payload.monitoring_rule_rule_id)
            .first()
        )
        if not monitoring_rule:
            raise HTTPException(status_code=404, detail="Monitoring rule not found")
        monitoring_rule_id = monitoring_rule.id
    elif monitoring_rule_id:
        monitoring_rule = (
            db.query(MonitoringRule).filter(MonitoringRule.id == monitoring_rule_id).first()
        )
        if not monitoring_rule:
            raise HTTPException(status_code=404, detail="Monitoring rule not found")

    mapping = InternalRuleMapping(
        internal_rule_id=rule.id,
        monitoring_rule_id=monitoring_rule_id,
        mapping_type=payload.mapping_type or "transaction_monitoring",
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return _mapping_to_dict(mapping, monitoring_rule)
