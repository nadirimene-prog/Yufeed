from datetime import datetime, timezone
import uuid


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


from typing import Optional, List
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from src.database import get_db
from src.auth.dependencies import require_any_role, CurrentUser
from src.models.compliance_workflow import (
    RegulatoryObligation,
    PolicyDocument,
    PolicyTemplate,
    InternalRule,
    PolicySection,
    RiskEntry,
    ObligationRiskLink,
    TenantObligationApplicability,
    ObligationPolicyMapping,
)
from src.models.models import LegalDocument
from src.models.tenant_models import Tenant
from src.schemas.obligation_schemas import (
    ObligationUpdate,
    ObligationApproval,
    TenantObligationApplicabilityUpdate,
)
from src.compliance.scope import normalize_scopes, scope_keywords
from src.websocket.manager import ws_manager
from src.websocket.events import EventType, NotificationEvent
from src.services.policy_library import ensure_master_policy_for_template
from src.services.policy_matcher import PolicyMatcher
from src.monitoring.metrics import obligation_approval_total, policy_mapping_suggestions_total
from src.audit.recorders import record_event, record_decision
from src.config import settings

router = APIRouter(prefix="/api/obligations", tags=["obligations"])


class BulkApproveRequest(BaseModel):
    obligation_ids: List[int] = Field(default_factory=list, min_length=1)
    status: str = Field(default="approved")
    note: Optional[str] = None
    auto_link_best_suggestion: bool = True
    create_internal_rule: bool = True


class BulkApproveItemResult(BaseModel):
    obligation_id: int
    status: str
    error: Optional[str] = None


def _normalize_statuses(status: Optional[str]) -> Optional[List[str]]:
    if not status:
        return None
    statuses = [item.strip().lower() for item in status.split(",") if item.strip()]
    return statuses or None


FOUR_EYES_OBLIGATION_DETAIL = (
    "4-eyes violation: approver cannot be the same as the obligation creator"
)


def _normalize_actor(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


def _user_actor_aliases(current_user: CurrentUser) -> set[str]:
    aliases = {
        _normalize_actor(current_user.user_id),
        _normalize_actor(current_user.email),
    }
    return {alias for alias in aliases if alias}


def _enforce_obligation_four_eyes(
    obligation: RegulatoryObligation, current_user: CurrentUser
) -> None:
    creator = _normalize_actor(obligation.created_by)
    if creator and creator in _user_actor_aliases(current_user):
        raise HTTPException(status_code=409, detail=FOUR_EYES_OBLIGATION_DETAIL)


def _obligation_to_dict(
    obligation: RegulatoryObligation,
    doc: LegalDocument,
    db: Session = None,
    tenant_id: Optional[str] = None,
) -> dict:
    title = doc.title or doc.celex or doc.source_reference or "Untitled document"

    # Get linked policy info if available
    linked_policy = None
    if obligation.linked_policy_id and db:
        policy = (
            db.query(PolicyDocument)
            .filter(PolicyDocument.id == obligation.linked_policy_id)
            .first()
        )
        if policy and (tenant_id is None or policy.tenant_id in (None, tenant_id)):
            linked_policy = {
                "id": policy.id,
                "policy_id": policy.policy_id,
                "name": policy.name,
                "status": policy.status,
            }

    # Get linked risks count
    linked_risks_count = 0
    if db:
        linked_risks_count = (
            db.query(ObligationRiskLink)
            .filter(ObligationRiskLink.obligation_id == obligation.id)
            .count()
        )

    # Get internal rules count
    internal_rules_count = 0
    if db:
        rule_query = db.query(InternalRule).filter(InternalRule.obligation_id == obligation.id)
        if tenant_id:
            rule_query = rule_query.filter(
                or_(InternalRule.tenant_id.is_(None), InternalRule.tenant_id == tenant_id)
            )
        internal_rules_count = rule_query.count()

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
        "created_by": obligation.created_by,
        "reviewed_by": obligation.reviewed_by,
        "approved_by": obligation.approved_by,
        "approved_at": obligation.approved_at.isoformat() if obligation.approved_at else None,
        "review_notes": obligation.review_notes,
        "updated_at": obligation.updated_at.isoformat() if obligation.updated_at else None,
        "scope_tags": obligation.scope_tags,
        "tags": obligation.tags_json,
        "evidence": obligation.evidence_json,
        "linked_policy_id": obligation.linked_policy_id,
        "linked_policy": linked_policy,
        "linked_risks_count": linked_risks_count,
        "internal_rules_count": internal_rules_count,
        "document": {
            "id": doc.id,
            "celex": doc.celex,
            "title": title,
            "jurisdiction": doc.jurisdiction,
            "source_system": doc.source_system,
            "publication_date": doc.publication_date.isoformat() if doc.publication_date else None,
            "scope_tags": doc.scope_tags,
        },
    }


def _apply_scope_filter(query, scope: Optional[str], db: Session):
    scopes = normalize_scopes(scope)
    if not scopes:
        return query
    dialect = db.get_bind().dialect.name if db.get_bind() else ""
    if dialect == "postgresql":
        conditions = []
        for scope_key in scopes:
            conditions.append(
                sa.cast(LegalDocument.scope_tags, postgresql.JSONB).op("@>")(
                    sa.func.jsonb_build_array(scope_key)
                )
            )
            conditions.append(
                sa.cast(RegulatoryObligation.scope_tags, postgresql.JSONB).op("@>")(
                    sa.func.jsonb_build_array(scope_key)
                )
            )
        return query.filter(or_(*conditions))

    keywords = scope_keywords(scopes)
    if not keywords:
        return query
    conditions = []
    for keyword in keywords:
        like = f"%{keyword}%"
        conditions.append(LegalDocument.title.ilike(like))
        conditions.append(RegulatoryObligation.obligation_text.ilike(like))
    return query.filter(or_(*conditions))


def _template_score(template: PolicyTemplate, text: str) -> int:
    haystack = (text or "").lower()
    score = 0
    name = (template.name or "").lower()
    category = (template.category or "").lower()

    if name and name in haystack:
        score += 5
    if category and category in haystack:
        score += 2

    category_keywords = {
        "aml/cft": [
            "aml",
            "cft",
            "kyc",
            "kyb",
            "pep",
            "sanction",
            "str",
            "travel rule",
            "record keeping",
        ],
        "emi": [
            "e-money",
            "emoney",
            "payment",
            "sca",
            "psd2",
            "safeguarding",
            "fraud",
            "complaint",
            "outsourcing",
        ],
        "casp": [
            "crypto",
            "asset",
            "custody",
            "token",
            "micar",
            "wallet",
            "listing",
            "market abuse",
        ],
        "governance": [
            "risk",
            "control",
            "ict",
            "dora",
            "incident",
            "outsourcing",
            "security",
            "bcp",
            "continuity",
        ],
        "gdpr": ["gdpr", "data", "privacy", "breach", "retention", "subject rights"],
        "hr": ["training", "staff", "remuneration", "fit and proper", "whistleblowing"],
    }
    for keyword in category_keywords.get(category, []):
        if keyword in haystack:
            score += 1

    if template.regulatory_basis:
        for basis in template.regulatory_basis:
            token = str(basis).lower().split(" ")[0]
            if token and token in haystack:
                score += 1

    return score


DEFAULT_OBLIGATION_SECTION_REF = "OBL"
DEFAULT_OBLIGATION_SECTION_TITLE = "Mapped obligations"


def _pick_best_template(
    templates: List[PolicyTemplate], text: str
) -> tuple[Optional[PolicyTemplate], int]:
    if not templates:
        return None, 0

    best_template: Optional[PolicyTemplate] = None
    best_score = -1
    for template in templates:
        score = _template_score(template, text)
        if score > best_score:
            best_score = score
            best_template = template

    # If nothing matched, fall back to the broad master policy if available.
    if best_score <= 0:
        fallback = next((t for t in templates if t.template_id == "aml-cft-policy-master"), None)
        if fallback is not None:
            best_template = fallback
            best_score = 0

    return best_template, best_score


def _get_or_create_obligation_section(db: Session, policy_doc_id: int) -> PolicySection:
    section = (
        db.query(PolicySection)
        .filter(
            PolicySection.policy_id == policy_doc_id,
            PolicySection.section_ref == DEFAULT_OBLIGATION_SECTION_REF,
        )
        .first()
    )
    if section:
        return section

    section = PolicySection(
        policy_id=policy_doc_id,
        section_ref=DEFAULT_OBLIGATION_SECTION_REF,
        title=DEFAULT_OBLIGATION_SECTION_TITLE,
        status="draft",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(section)
    db.flush()
    return section


def _ensure_internal_rule_for_obligation(
    db: Session,
    obligation: RegulatoryObligation,
    *,
    tenant_id: Optional[str],
    policy_section_id: Optional[int],
    current_user_email: str,
    name: str,
    description: Optional[str],
) -> tuple[InternalRule, bool]:
    existing = (
        db.query(InternalRule)
        .filter(InternalRule.obligation_id == obligation.id)
        .order_by(InternalRule.id.asc())
        .first()
    )
    if existing:
        changed = False
        if existing.tenant_id is None and tenant_id is not None:
            existing.tenant_id = tenant_id
            changed = True
        if existing.policy_section_id is None and policy_section_id is not None:
            existing.policy_section_id = policy_section_id
            changed = True
        if not (existing.control_owner or "").strip() and (current_user_email or "").strip():
            existing.control_owner = current_user_email
            changed = True
        if changed:
            existing.updated_at = utc_now()
        return existing, False

    rule = InternalRule(
        internal_rule_id=f"IR-{uuid.uuid4().hex[:8].upper()}",
        tenant_id=tenant_id,
        obligation_id=obligation.id,
        policy_section_id=policy_section_id,
        name=name,
        description=description,
        control_owner=current_user_email,
        status="draft",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(rule)
    return rule, True


def _effective_tenant_id(
    current_user: Optional[CurrentUser],
    requested_tenant_id: Optional[str] = None,
) -> Optional[str]:
    if isinstance(requested_tenant_id, str) and requested_tenant_id.strip():
        return requested_tenant_id.strip()
    if current_user is None:
        return None
    return current_user.tenant_id


def _is_policy_visible_to_tenant(policy: PolicyDocument, tenant_id: Optional[str]) -> bool:
    if tenant_id is None:
        return True
    return policy.tenant_id in (None, tenant_id)


def _upsert_obligation_policy_mapping(
    db: Session,
    obligation_id: int,
    policy_id: int,
    *,
    mapped_by: str,
    confidence: float = 1.0,
    notes: Optional[str] = None,
) -> None:
    mapping = (
        db.query(ObligationPolicyMapping)
        .filter(
            ObligationPolicyMapping.obligation_id == obligation_id,
            ObligationPolicyMapping.policy_id == policy_id,
        )
        .first()
    )
    if mapping is None:
        mapping = ObligationPolicyMapping(obligation_id=obligation_id, policy_id=policy_id)
        db.add(mapping)
    mapping.mapped_by = mapped_by
    mapping.mapping_confidence = confidence
    mapping.notes = notes
    mapping.mapped_at = utc_now()


@router.get("")
def list_obligations(
    status: Optional[str] = Query(None, description="Comma-separated statuses"),
    jurisdiction: Optional[str] = Query(None),
    source_system: Optional[str] = Query(None),
    scope: Optional[str] = Query(None, description="Comma-separated scope tags: psp,eme,vasp"),
    q: Optional[str] = Query(None, description="Search text"),
    include_status_counts: bool = Query(
        False, description="Include counts of obligations by status"
    ),
    tenant_id: Optional[str] = Query(
        None,
        description="Filter by tenant applicability (defaults to current user tenant)",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])
    ),
):
    current_user = _
    effective_tenant_id = _effective_tenant_id(current_user, tenant_id)
    statuses = _normalize_statuses(status)

    query = db.query(RegulatoryObligation, LegalDocument).join(
        LegalDocument, RegulatoryObligation.doc_id == LegalDocument.id
    )

    if statuses:
        query = query.filter(RegulatoryObligation.status.in_(statuses))
    if jurisdiction:
        query = query.filter(LegalDocument.jurisdiction == jurisdiction)
    if source_system:
        query = query.filter(LegalDocument.source_system == source_system)
    if scope:
        query = _apply_scope_filter(query, scope, db)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                RegulatoryObligation.obligation_text.ilike(like),
                RegulatoryObligation.article_ref.ilike(like),
                LegalDocument.title.ilike(like),
                LegalDocument.celex.ilike(like),
            )
        )

    if effective_tenant_id:
        query = query.outerjoin(
            TenantObligationApplicability,
            sa.and_(
                TenantObligationApplicability.obligation_id == RegulatoryObligation.id,
                TenantObligationApplicability.tenant_id == effective_tenant_id,
            ),
        ).filter(
            or_(
                TenantObligationApplicability.id.is_(None),
                TenantObligationApplicability.applicability.in_(
                    ["applicable", "partially_applicable"]
                ),
            )
        )

    total = query.count()
    status_counts = None
    if include_status_counts:
        counts = (
            query.with_entities(
                RegulatoryObligation.status,
                sa.func.count(RegulatoryObligation.id),
            )
            .group_by(RegulatoryObligation.status)
            .all()
        )
        status_counts = {status: count for status, count in counts}

    rows = query.order_by(RegulatoryObligation.updated_at.desc()).offset(skip).limit(limit).all()

    response = {
        "total": total,
        "items": [
            _obligation_to_dict(obligation, doc, db, tenant_id=effective_tenant_id)
            for obligation, doc in rows
        ],
    }
    if status_counts is not None:
        response["status_counts"] = status_counts

    return response


@router.get("/{obligation_id}")
def get_obligation(
    obligation_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])
    ),
):
    effective_tenant_id = _effective_tenant_id(current_user)
    row = (
        db.query(RegulatoryObligation, LegalDocument)
        .join(LegalDocument, RegulatoryObligation.doc_id == LegalDocument.id)
        .filter(RegulatoryObligation.id == obligation_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Obligation not found")

    obligation, doc = row
    if effective_tenant_id:
        tenant_applicability = (
            db.query(TenantObligationApplicability)
            .filter(
                TenantObligationApplicability.tenant_id == effective_tenant_id,
                TenantObligationApplicability.obligation_id == obligation.id,
            )
            .first()
        )
        if tenant_applicability and tenant_applicability.applicability not in (
            "applicable",
            "partially_applicable",
        ):
            raise HTTPException(status_code=404, detail="Obligation not found")

    result = _obligation_to_dict(obligation, doc, db, tenant_id=effective_tenant_id)

    # Get linked risks details
    risk_links = (
        db.query(ObligationRiskLink).filter(ObligationRiskLink.obligation_id == obligation.id).all()
    )
    result["linked_risks"] = []
    for link in risk_links:
        risk_entry = db.query(RiskEntry).filter(RiskEntry.id == link.risk_entry_id).first()
        if risk_entry:
            result["linked_risks"].append(
                {
                    "link_id": link.id,
                    "link_type": link.link_type,
                    "risk_id": risk_entry.risk_id,
                    "name": risk_entry.name,
                    "inherent_risk_level": risk_entry.inherent_risk_level,
                    "residual_risk_level": risk_entry.residual_risk_level,
                }
            )

    # Get internal rules
    internal_rules = (
        db.query(InternalRule)
        .filter(
            InternalRule.obligation_id == obligation.id,
            (
                or_(
                    InternalRule.tenant_id.is_(None),
                    InternalRule.tenant_id == effective_tenant_id,
                )
                if effective_tenant_id
                else sa.true()
            ),
        )
        .all()
    )
    result["internal_rules"] = [
        {
            "id": rule.id,
            "internal_rule_id": rule.internal_rule_id,
            "name": rule.name,
            "status": rule.status,
            "control_owner": rule.control_owner,
        }
        for rule in internal_rules
    ]

    return result


@router.get("/{obligation_id}/policy-suggestions")
def get_policy_template_suggestions(
    obligation_id: int,
    limit: int = Query(3, ge=1, le=10),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])
    ),
):
    row = (
        db.query(RegulatoryObligation, LegalDocument)
        .join(LegalDocument, RegulatoryObligation.doc_id == LegalDocument.id)
        .filter(RegulatoryObligation.id == obligation_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Obligation not found")

    obligation, doc = row
    matcher = PolicyMatcher(db)
    suggestions = matcher.suggest_policies(obligation, limit=limit)
    effective_tenant_id = _effective_tenant_id(current_user)

    # Fallback to legacy template scoring if semantic matcher returns nothing.
    if not suggestions:
        text = " ".join(
            [
                obligation.obligation_text or "",
                obligation.article_ref or "",
                doc.title or "",
                doc.jurisdiction or "",
            ]
        )
        templates = db.query(PolicyTemplate).filter(PolicyTemplate.is_active == True).all()
        if effective_tenant_id:
            tenant = db.query(Tenant).filter(Tenant.tenant_id == effective_tenant_id).first()
            institution_type = (tenant.institution_type or "").lower() if tenant else ""
            if institution_type:
                templates = [
                    template
                    for template in templates
                    if not template.institution_types
                    or institution_type in (template.institution_types or [])
                ]

        template_ids = [t.template_id for t in templates]
        master_policies = {}
        if template_ids:
            for policy in (
                db.query(PolicyDocument).filter(PolicyDocument.policy_id.in_(template_ids)).all()
            ):
                master_policies[policy.policy_id] = policy

        scored = []
        for template in templates:
            score = _template_score(template, text)
            scored.append((score, template))
        scored.sort(key=lambda item: item[0], reverse=True)
        if scored and scored[0][0] <= 0:
            best_template, best_score = _pick_best_template(templates, text)
            scored = [(best_score, best_template)] if best_template else []
        else:
            scored = [(score, template) for score, template in scored if score > 0]

        for score, template in scored[:limit]:
            policy = master_policies.get(template.template_id)
            if not policy:
                policy = next(
                    (
                        p
                        for p in db.query(PolicyDocument).all()
                        if (p.metadata_json or {}).get("template_id") == template.template_id
                    ),
                    None,
                )
            if not policy:
                continue
            suggestions.append(
                {
                    "policy_document_id": policy.id,
                    "policy_id": policy.policy_id,
                    "template_id": template.template_id,
                    "name": policy.name or template.name,
                    "category": template.category,
                    "score": score,
                    "confidence": min(1.0, float(score) / 10.0),
                    "reasoning": "Keyword overlap fallback",
                    "match_method": "keyword",
                }
            )

    mapping_rows = (
        db.query(ObligationPolicyMapping, PolicyDocument)
        .join(PolicyDocument, PolicyDocument.id == ObligationPolicyMapping.policy_id)
        .filter(ObligationPolicyMapping.obligation_id == obligation.id)
        .all()
    )
    existing_map = {policy.id: mapping for mapping, policy in mapping_rows}

    items: List[dict] = []
    seen_policy_ids: set[int] = set()
    for suggestion in suggestions[:limit]:
        policy_pk = suggestion.get("policy_document_id")
        if not isinstance(policy_pk, int):
            continue
        if policy_pk in seen_policy_ids:
            continue
        seen_policy_ids.add(policy_pk)

        mapping = existing_map.get(policy_pk)
        match_method = suggestion.get("match_method", "keyword")
        try:
            policy_mapping_suggestions_total.labels(match_method=match_method).inc()
        except Exception:
            pass

        items.append(
            {
                "policy_document_id": policy_pk,
                "policy_id": suggestion.get("policy_id"),
                "template_id": suggestion.get("template_id"),
                "name": suggestion.get("name"),
                "category": suggestion.get("category"),
                "score": suggestion.get("score"),
                "confidence": suggestion.get("confidence"),
                "reasoning": suggestion.get("reasoning"),
                "match_method": match_method,
                "mapped_by": mapping.mapped_by if mapping else None,
                "mapping_confidence": mapping.mapping_confidence if mapping else None,
            }
        )

    # Include existing AI mappings not present in freshly computed suggestions.
    for mapping, policy in mapping_rows:
        if policy.id in seen_policy_ids:
            continue
        items.append(
            {
                "policy_document_id": policy.id,
                "policy_id": policy.policy_id,
                "template_id": (
                    (policy.metadata_json or {}).get("template_id")
                    if isinstance(policy.metadata_json, dict)
                    else None
                ),
                "name": policy.name,
                "category": (
                    (policy.metadata_json or {}).get("category")
                    if isinstance(policy.metadata_json, dict)
                    else None
                ),
                "score": mapping.mapping_confidence,
                "confidence": mapping.mapping_confidence,
                "reasoning": mapping.notes,
                "match_method": (
                    "semantic" if (mapping.mapped_by or "").startswith("ai:") else "keyword"
                ),
                "mapped_by": mapping.mapped_by,
                "mapping_confidence": mapping.mapping_confidence,
            }
        )

    return {"items": items[:limit]}


@router.post("/{obligation_id}/applicability")
def set_tenant_obligation_applicability(
    obligation_id: int,
    payload: TenantObligationApplicabilityUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    obligation = (
        db.query(RegulatoryObligation).filter(RegulatoryObligation.id == obligation_id).first()
    )
    if not obligation:
        raise HTTPException(status_code=404, detail="Obligation not found")

    tenant = db.query(Tenant).filter(Tenant.tenant_id == payload.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    row = (
        db.query(TenantObligationApplicability)
        .filter(
            TenantObligationApplicability.tenant_id == payload.tenant_id,
            TenantObligationApplicability.obligation_id == obligation_id,
        )
        .first()
    )
    created = False
    if row is None:
        row = TenantObligationApplicability(
            tenant_id=payload.tenant_id,
            obligation_id=obligation_id,
        )
        db.add(row)
        created = True

    row.applicability = payload.applicability
    row.notes = payload.notes
    row.assessed_by = current_user.email
    row.assessed_at = utc_now()
    row.updated_at = utc_now()
    db.commit()
    db.refresh(row)

    return {
        "tenant_id": row.tenant_id,
        "obligation_id": row.obligation_id,
        "applicability": row.applicability,
        "assessed_by": row.assessed_by,
        "assessed_at": row.assessed_at.isoformat() if row.assessed_at else None,
        "notes": row.notes,
        "created": created,
    }


@router.patch("/{obligation_id}")
async def update_obligation(
    obligation_id: int,
    payload: ObligationUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    effective_tenant_id = _effective_tenant_id(current_user)
    obligation = (
        db.query(RegulatoryObligation).filter(RegulatoryObligation.id == obligation_id).first()
    )
    if not obligation:
        raise HTTPException(status_code=404, detail="Obligation not found")

    new_status = payload.status.lower().strip()
    allowed_statuses = {"draft", "in_review", "approved", "rejected", "deprecated"}
    if new_status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Unsupported status")

    transition_map = {
        "draft": {"in_review", "approved", "rejected", "deprecated"},
        "in_review": {"approved", "rejected", "draft"},
        "approved": {"deprecated"},
        "rejected": {"draft", "in_review"},
        "deprecated": set(),
    }
    current_status = (obligation.status or "draft").lower()
    if new_status != current_status and new_status not in transition_map.get(current_status, set()):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status transition from {current_status} to {new_status}",
        )

    is_approval_transition = new_status == "approved" and current_status != "approved"
    if is_approval_transition:
        _enforce_obligation_four_eyes(obligation, current_user)

    obligation.status = new_status
    obligation.updated_at = utc_now()

    if payload.note and payload.note.strip():
        note_entry = f"[{utc_now().isoformat()}] {current_user.email}: {payload.note.strip()}"
        if obligation.review_notes:
            obligation.review_notes = f"{obligation.review_notes.rstrip()}\n{note_entry}"
        else:
            obligation.review_notes = note_entry

    if new_status == "in_review":
        obligation.reviewed_by = current_user.email
    if new_status == "approved":
        # Ensure an approved obligation is mapped into a policy and has an internal rule.
        doc = db.query(LegalDocument).filter(LegalDocument.id == obligation.doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Linked document not found")

        linked_policy: Optional[PolicyDocument] = None
        if obligation.linked_policy_id:
            linked_policy = (
                db.query(PolicyDocument)
                .filter(PolicyDocument.id == obligation.linked_policy_id)
                .first()
            )
            if linked_policy and not _is_policy_visible_to_tenant(
                linked_policy, effective_tenant_id
            ):
                linked_policy = None
                obligation.linked_policy_id = None

        if not obligation.linked_policy_id:
            templates = db.query(PolicyTemplate).filter(PolicyTemplate.is_active == True).all()
            if effective_tenant_id:
                tenant = db.query(Tenant).filter(Tenant.tenant_id == effective_tenant_id).first()
                institution_type = (tenant.institution_type or "").lower() if tenant else ""
                if institution_type:
                    templates = [
                        template
                        for template in templates
                        if not template.institution_types
                        or institution_type in (template.institution_types or [])
                    ]
            if not templates:
                raise HTTPException(
                    status_code=409, detail="No policy templates/master policies available"
                )

            text = " ".join(
                [
                    obligation.obligation_text or "",
                    obligation.article_ref or "",
                    doc.title or "",
                    doc.jurisdiction or "",
                ]
            )
            best_template, best_score = _pick_best_template(templates, text)
            if not best_template:
                raise HTTPException(
                    status_code=409, detail="No policy templates/master policies available"
                )

            policy, _ = ensure_master_policy_for_template(db, best_template)
            linked_policy = policy
            obligation.linked_policy_id = policy.id

            auto_note = f"[{utc_now().isoformat()}] {current_user.email}: Auto-linked to policy {policy.policy_id} (score={best_score})"
            obligation.review_notes = (
                f"{(obligation.review_notes or '').rstrip()}\n{auto_note}".strip()
            )

        if linked_policy is None and obligation.linked_policy_id:
            linked_policy = (
                db.query(PolicyDocument)
                .filter(PolicyDocument.id == obligation.linked_policy_id)
                .first()
            )

        if obligation.linked_policy_id:
            _upsert_obligation_policy_mapping(
                db,
                obligation.id,
                obligation.linked_policy_id,
                mapped_by=f"user:{current_user.user_id}",
                confidence=1.0,
                notes="Auto-linked during obligation approval",
            )

        policy_section = _get_or_create_obligation_section(db, obligation.linked_policy_id)
        _ensure_internal_rule_for_obligation(
            db,
            obligation,
            tenant_id=linked_policy.tenant_id if linked_policy else None,
            policy_section_id=policy_section.id if policy_section else None,
            current_user_email=current_user.email,
            name=f"Implement {obligation.obligation_id}",
            description=(obligation.obligation_text or "")[:1000] or None,
        )

        obligation.approved_by = current_user.email
        obligation.approved_at = utc_now()
    if new_status == "rejected":
        obligation.reviewed_by = current_user.email

    db.commit()
    db.refresh(obligation)

    doc = db.query(LegalDocument).filter(LegalDocument.id == obligation.doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Linked document not found")

    # Send WebSocket notification
    try:
        event_type = (
            EventType.OBLIGATION_APPROVED
            if new_status == "approved"
            else (
                EventType.OBLIGATION_REJECTED
                if new_status == "rejected"
                else EventType.OBLIGATION_UPDATED
            )
        )
        await ws_manager.send_notification(
            NotificationEvent(
                event_type=event_type,
                title=f"Obligation {new_status.title()}",
                message=f"Obligation {obligation.obligation_id} has been {new_status}",
                data={
                    "obligation_id": obligation.obligation_id,
                    "status": new_status,
                    "approved_by": current_user.email,
                },
                priority="high" if new_status == "rejected" else "normal",
                link=f"/compliance/obligations/{obligation.id}",
            )
        )
    except Exception:
        pass

    return _obligation_to_dict(obligation, doc, db, tenant_id=effective_tenant_id)


@router.patch("/{obligation_id}/approve")
async def approve_obligation(
    obligation_id: int,
    payload: ObligationApproval,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    """Enhanced approval with policy linking and internal rule creation."""
    effective_tenant_id = _effective_tenant_id(current_user)
    obligation = (
        db.query(RegulatoryObligation).filter(RegulatoryObligation.id == obligation_id).first()
    )
    if not obligation:
        raise HTTPException(status_code=404, detail="Obligation not found")

    doc = db.query(LegalDocument).filter(LegalDocument.id == obligation.doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Linked document not found")

    new_status = payload.status.lower().strip()
    allowed_statuses = {"draft", "in_review", "approved", "rejected", "deprecated"}
    if new_status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Unsupported status")

    transition_map = {
        "draft": {"in_review", "approved", "rejected", "deprecated"},
        "in_review": {"approved", "rejected", "draft"},
        "approved": {"deprecated"},
        "rejected": {"draft", "in_review"},
        "deprecated": set(),
    }
    current_status = (obligation.status or "draft").lower()
    if new_status != current_status and new_status not in transition_map.get(current_status, set()):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status transition from {current_status} to {new_status}",
        )

    is_approval_transition = new_status == "approved" and current_status != "approved"
    if is_approval_transition:
        _enforce_obligation_four_eyes(obligation, current_user)

    # Validate linked policy if provided
    linked_policy: Optional[PolicyDocument] = None
    if payload.linked_policy_id:
        linked_policy = (
            db.query(PolicyDocument).filter(PolicyDocument.id == payload.linked_policy_id).first()
        )
        if not linked_policy:
            raise HTTPException(status_code=404, detail="Linked policy not found")
        if not _is_policy_visible_to_tenant(linked_policy, effective_tenant_id):
            raise HTTPException(status_code=404, detail="Linked policy not found")
        obligation.linked_policy_id = linked_policy.id

    # Update status
    obligation.status = new_status
    obligation.updated_at = utc_now()

    if payload.note and payload.note.strip():
        note_entry = f"[{utc_now().isoformat()}] {current_user.email}: {payload.note.strip()}"
        if obligation.review_notes:
            obligation.review_notes = f"{obligation.review_notes.rstrip()}\n{note_entry}"
        else:
            obligation.review_notes = note_entry

    if new_status == "in_review":
        obligation.reviewed_by = current_user.email
    if new_status == "approved":
        # Ensure approved obligations are always linked to a policy (auto-assign from master policies if missing).
        if not obligation.linked_policy_id:
            if not payload.auto_link_best_suggestion:
                raise HTTPException(
                    status_code=409,
                    detail="Approved obligation must be linked to a policy when auto-link is disabled",
                )

            templates = db.query(PolicyTemplate).filter(PolicyTemplate.is_active == True).all()
            if effective_tenant_id:
                tenant = db.query(Tenant).filter(Tenant.tenant_id == effective_tenant_id).first()
                institution_type = (tenant.institution_type or "").lower() if tenant else ""
                if institution_type:
                    templates = [
                        template
                        for template in templates
                        if not template.institution_types
                        or institution_type in (template.institution_types or [])
                    ]
            if not templates:
                raise HTTPException(
                    status_code=409, detail="No policy templates/master policies available"
                )

            text = " ".join(
                [
                    obligation.obligation_text or "",
                    obligation.article_ref or "",
                    doc.title or "",
                    doc.jurisdiction or "",
                ]
            )
            best_template, best_score = _pick_best_template(templates, text)
            if not best_template:
                raise HTTPException(
                    status_code=409, detail="No policy templates/master policies available"
                )

            master_policy, _ = ensure_master_policy_for_template(db, best_template)
            obligation.linked_policy_id = master_policy.id
            linked_policy = master_policy

            auto_note = f"[{utc_now().isoformat()}] {current_user.email}: Auto-linked to policy {master_policy.policy_id} (score={best_score})"
            obligation.review_notes = (
                f"{(obligation.review_notes or '').rstrip()}\n{auto_note}".strip()
            )

        obligation.approved_by = current_user.email
        obligation.approved_at = utc_now()
    if new_status == "rejected":
        obligation.reviewed_by = current_user.email

    # Optionally create (or reuse) an internal rule on approval.
    internal_rule = None
    internal_rule_created = False
    if new_status == "approved":
        if not obligation.linked_policy_id:
            raise HTTPException(
                status_code=409, detail="Approved obligation must be linked to a policy"
            )

        if linked_policy is None:
            linked_policy = (
                db.query(PolicyDocument)
                .filter(PolicyDocument.id == obligation.linked_policy_id)
                .first()
            )

        _upsert_obligation_policy_mapping(
            db,
            obligation.id,
            obligation.linked_policy_id,
            mapped_by=f"user:{current_user.user_id}",
            confidence=1.0,
            notes="Mapped during obligation approval",
        )

        if payload.create_internal_rule:
            policy_section = _get_or_create_obligation_section(db, obligation.linked_policy_id)
            rule_name = payload.internal_rule_name or f"Implement {obligation.obligation_id}"
            description = (
                payload.internal_rule_description
                or (
                    f"{(obligation.article_ref or '').strip()}\n\n{(obligation.obligation_text or '').strip()}"
                ).strip()
            )
            description = description[:2000] if description else None
            internal_rule, internal_rule_created = _ensure_internal_rule_for_obligation(
                db,
                obligation,
                tenant_id=linked_policy.tenant_id if linked_policy else None,
                policy_section_id=policy_section.id if policy_section else None,
                current_user_email=current_user.email,
                name=rule_name,
                description=description,
            )

    # Link to risk entries if provided
    if payload.link_risk_entry_ids:
        for risk_entry_id in payload.link_risk_entry_ids:
            risk_entry = db.query(RiskEntry).filter(RiskEntry.id == risk_entry_id).first()
            if not risk_entry:
                continue  # Skip invalid risk entries

            # Check if link already exists
            existing_link = (
                db.query(ObligationRiskLink)
                .filter(
                    ObligationRiskLink.obligation_id == obligation.id,
                    ObligationRiskLink.risk_entry_id == risk_entry_id,
                )
                .first()
            )
            if existing_link:
                continue

            link = ObligationRiskLink(
                obligation_id=obligation.id,
                risk_entry_id=risk_entry_id,
                link_type="mitigates",
                created_by=current_user.email,
                created_at=utc_now(),
            )
            db.add(link)

    db.commit()
    db.refresh(obligation)

    if internal_rule:
        db.refresh(internal_rule)

    try:
        obligation_approval_total.labels(status=new_status).inc()
    except Exception:
        pass

    try:
        tenant_id = effective_tenant_id or "default"
        record_event(
            db=db,
            tenant_id=tenant_id,
            event_type="compliance.obligation.updated",
            entity_type="regulatory_obligation",
            entity_id=str(obligation.id),
            source="api.obligations.approve_obligation",
            payload={
                "status": new_status,
                "linked_policy_id": obligation.linked_policy_id,
                "auto_link_best_suggestion": payload.auto_link_best_suggestion,
                "create_internal_rule": payload.create_internal_rule,
            },
            metadata={"actor_id": current_user.user_id, "actor_email": current_user.email},
        )
        if new_status in {"approved", "rejected"}:
            record_decision(
                db=db,
                tenant_id=tenant_id,
                decision="allow" if new_status == "approved" else "deny",
                reason_codes=[f"obligation_{new_status}"],
                metadata={
                    "obligation_id": obligation.id,
                    "linked_policy_id": obligation.linked_policy_id,
                },
            )
    except Exception:
        pass

    # Send WebSocket notifications
    try:
        event_type = (
            EventType.OBLIGATION_APPROVED
            if new_status == "approved"
            else (
                EventType.OBLIGATION_REJECTED
                if new_status == "rejected"
                else EventType.OBLIGATION_UPDATED
            )
        )
        await ws_manager.send_notification(
            NotificationEvent(
                event_type=event_type,
                title=f"Obligation {new_status.title()}",
                message=f"Obligation {obligation.obligation_id} has been {new_status}",
                data={
                    "obligation_id": obligation.obligation_id,
                    "status": new_status,
                    "approved_by": current_user.email,
                    "internal_rule_id": internal_rule.internal_rule_id if internal_rule else None,
                },
                priority="high" if new_status == "rejected" else "normal",
                link=f"/compliance/obligations/{obligation.id}",
            )
        )

        if internal_rule and internal_rule_created:
            await ws_manager.send_notification(
                NotificationEvent(
                    event_type=EventType.INTERNAL_RULE_CREATED,
                    title="Internal Rule Created",
                    message=f"Internal rule created: {internal_rule.name}",
                    data={
                        "internal_rule_id": internal_rule.internal_rule_id,
                        "obligation_id": obligation.obligation_id,
                    },
                    priority="normal",
                    link=f"/compliance/obligations/{obligation.id}",
                )
            )
    except Exception:
        pass

    result = _obligation_to_dict(obligation, doc, db, tenant_id=effective_tenant_id)
    if internal_rule and internal_rule_created:
        result["created_internal_rule"] = {
            "id": internal_rule.id,
            "internal_rule_id": internal_rule.internal_rule_id,
            "name": internal_rule.name,
        }

    return result


@router.post("/bulk-approve")
async def bulk_approve_obligations(
    payload: BulkApproveRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    """Bulk approval endpoint with per-item partial success."""
    results: List[BulkApproveItemResult] = []
    succeeded = 0
    failed = 0

    for obligation_id in payload.obligation_ids:
        try:
            approval_payload = ObligationApproval(
                status=payload.status,
                note=payload.note,
                create_internal_rule=payload.create_internal_rule,
                auto_link_best_suggestion=payload.auto_link_best_suggestion,
            )
            await approve_obligation(
                obligation_id=obligation_id,
                payload=approval_payload,
                db=db,
                current_user=current_user,
            )
            succeeded += 1
            results.append(BulkApproveItemResult(obligation_id=obligation_id, status="approved"))
            try:
                obligation_approval_total.labels(status="approved").inc()
            except Exception:
                pass

            try:
                tenant_id = _effective_tenant_id(current_user) or "default"
                record_event(
                    db=db,
                    tenant_id=tenant_id,
                    event_type="compliance.obligation.bulk_approved",
                    entity_type="regulatory_obligation",
                    entity_id=str(obligation_id),
                    source="api.obligations.bulk_approve",
                    payload={"status": "approved"},
                    metadata={"actor_id": current_user.user_id, "actor_email": current_user.email},
                )
                record_decision(
                    db=db,
                    tenant_id=tenant_id,
                    decision="allow",
                    reason_codes=["bulk_approval"],
                    metadata={"obligation_id": obligation_id, "status": "approved"},
                )
            except Exception:
                pass
        except HTTPException as exc:
            failed += 1
            error_msg = (
                str(exc.detail) if getattr(exc, "detail", None) else f"HTTP {exc.status_code}"
            )
            results.append(
                BulkApproveItemResult(
                    obligation_id=obligation_id,
                    status="failed",
                    error=error_msg,
                )
            )
            try:
                obligation_approval_total.labels(status="failed").inc()
            except Exception:
                pass
            db.rollback()
        except Exception as exc:
            failed += 1
            results.append(
                BulkApproveItemResult(obligation_id=obligation_id, status="failed", error=str(exc))
            )
            try:
                obligation_approval_total.labels(status="failed").inc()
            except Exception:
                pass
            try:
                tenant_id = _effective_tenant_id(current_user) or "default"
                record_event(
                    db=db,
                    tenant_id=tenant_id,
                    event_type="compliance.obligation.bulk_approval_failed",
                    entity_type="regulatory_obligation",
                    entity_id=str(obligation_id),
                    source="api.obligations.bulk_approve",
                    payload={"status": "failed", "error": str(exc)},
                    metadata={"actor_id": current_user.user_id, "actor_email": current_user.email},
                )
            except Exception:
                pass
            db.rollback()

    return {
        "total": len(payload.obligation_ids),
        "succeeded": succeeded,
        "failed": failed,
        "items": [item.model_dump() for item in results],
    }


@router.get("/coverage-stats")
def get_obligation_coverage_stats(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])
    ),
):
    """Coverage metrics for obligation -> policy linkage."""
    effective_tenant_id = _effective_tenant_id(current_user)
    base_query = db.query(RegulatoryObligation)
    if effective_tenant_id:
        base_query = base_query.outerjoin(
            PolicyDocument,
            PolicyDocument.id == RegulatoryObligation.linked_policy_id,
        ).filter(
            or_(PolicyDocument.tenant_id.is_(None), PolicyDocument.tenant_id == effective_tenant_id)
        )

    total = base_query.count()
    linked_count = base_query.filter(RegulatoryObligation.linked_policy_id.isnot(None)).count()
    unlinked_count = max(total - linked_count, 0)

    ai_suggested_count = (
        db.query(sa.func.count(sa.func.distinct(ObligationPolicyMapping.obligation_id)))
        .filter(ObligationPolicyMapping.mapped_by.ilike("ai:%"))
        .scalar()
        or 0
    )

    high_t = float(getattr(settings, "POLICY_MATCH_HIGH_CONFIDENCE", 0.70))
    med_t = float(getattr(settings, "POLICY_MATCH_MEDIUM_CONFIDENCE", 0.45))
    high_count = (
        db.query(sa.func.count(ObligationPolicyMapping.id))
        .filter(
            ObligationPolicyMapping.mapped_by.ilike("ai:%"),
            ObligationPolicyMapping.mapping_confidence >= high_t,
        )
        .scalar()
        or 0
    )
    medium_count = (
        db.query(sa.func.count(ObligationPolicyMapping.id))
        .filter(
            ObligationPolicyMapping.mapped_by.ilike("ai:%"),
            ObligationPolicyMapping.mapping_confidence < high_t,
            ObligationPolicyMapping.mapping_confidence >= med_t,
        )
        .scalar()
        or 0
    )
    low_count = (
        db.query(sa.func.count(ObligationPolicyMapping.id))
        .filter(
            ObligationPolicyMapping.mapped_by.ilike("ai:%"),
            or_(
                ObligationPolicyMapping.mapping_confidence < med_t,
                ObligationPolicyMapping.mapping_confidence.is_(None),
            ),
        )
        .scalar()
        or 0
    )

    return {
        "total": total,
        "linked_count": linked_count,
        "unlinked_count": unlinked_count,
        "ai_suggested_count": ai_suggested_count,
        "confidence_tiers": {
            "high": high_count,
            "medium": medium_count,
            "low": low_count,
        },
    }


@router.get("/{obligation_id}/risks")
def get_obligation_risks(
    obligation_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])
    ),
):
    """Get risks linked to an obligation."""
    obligation = (
        db.query(RegulatoryObligation).filter(RegulatoryObligation.id == obligation_id).first()
    )
    if not obligation:
        raise HTTPException(status_code=404, detail="Obligation not found")

    links = (
        db.query(ObligationRiskLink).filter(ObligationRiskLink.obligation_id == obligation_id).all()
    )

    result = []
    for link in links:
        risk_entry = db.query(RiskEntry).filter(RiskEntry.id == link.risk_entry_id).first()
        if risk_entry:
            result.append(
                {
                    "link_id": link.id,
                    "link_type": link.link_type,
                    "notes": link.notes,
                    "created_at": link.created_at.isoformat() if link.created_at else None,
                    "risk": {
                        "id": risk_entry.id,
                        "risk_id": risk_entry.risk_id,
                        "name": risk_entry.name,
                        "category_id": risk_entry.category_id,
                        "inherent_risk_level": risk_entry.inherent_risk_level,
                        "residual_risk_level": risk_entry.residual_risk_level,
                        "mitigation_status": risk_entry.mitigation_status,
                    },
                }
            )

    return {"items": result}


@router.get("/{obligation_id}/internal-rules")
def get_obligation_internal_rules(
    obligation_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])
    ),
):
    """Get internal rules for an obligation."""
    effective_tenant_id = _effective_tenant_id(current_user)
    obligation = (
        db.query(RegulatoryObligation).filter(RegulatoryObligation.id == obligation_id).first()
    )
    if not obligation:
        raise HTTPException(status_code=404, detail="Obligation not found")

    query = db.query(InternalRule).filter(InternalRule.obligation_id == obligation_id)
    if effective_tenant_id:
        query = query.filter(
            or_(InternalRule.tenant_id.is_(None), InternalRule.tenant_id == effective_tenant_id)
        )
    rules = query.all()

    return {
        "items": [
            {
                "id": rule.id,
                "internal_rule_id": rule.internal_rule_id,
                "name": rule.name,
                "description": rule.description,
                "status": rule.status,
                "control_owner": rule.control_owner,
                "policy_section_id": rule.policy_section_id,
                "created_at": rule.created_at.isoformat() if rule.created_at else None,
                "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
            }
            for rule in rules
        ]
    }
