from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, List

from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.models.compliance_workflow import PolicyDocument, PolicyTemplate, RegulatoryObligation

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _sort_key_policy(policy: PolicyDocument) -> datetime:
    return policy.updated_at or policy.created_at or datetime.min.replace(tzinfo=timezone.utc)


def _merge_master_metadata(template: PolicyTemplate, existing: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    metadata: Dict[str, Any] = dict(existing or {})
    metadata.update(
        {
            "template_id": template.template_id,
            "category": template.category,
            "regulatory_basis": template.regulatory_basis,
            "review_frequency_months": template.review_frequency_months,
            "template_version": template.version,
            "is_master_policy": True,
        }
    )
    return metadata


def ensure_master_policy_for_template(
    db: Session,
    template: PolicyTemplate,
    *,
    existing_policies: Optional[List[PolicyDocument]] = None,
) -> Tuple[PolicyDocument, Dict[str, int]]:
    """
    Ensure exactly one canonical PolicyDocument exists for the given PolicyTemplate.

    - Canonical policy_id is template.template_id (stable).
    - Canonical status is "active".
    - Duplicate policies for the same template are set to status="retired" and annotated in metadata.
    """

    template_id = template.template_id
    stats = {"created": 0, "updated": 0, "duplicates_retired": 0}

    policies = list(existing_policies or [])

    # Fallback: discover matching policies by either:
    # - policy_id == template_id (preferred, stable), or
    # - metadata_json["template_id"] == template_id (legacy state)
    # We keep this Python-side for cross-DB compatibility.
    if existing_policies is None:
        candidates = db.query(PolicyDocument).all()
        for policy in candidates:
            if policy.policy_id == template_id and policy not in policies:
                policies.append(policy)
            meta_template_id = (policy.metadata_json or {}).get("template_id")
            if meta_template_id == template_id and policy not in policies:
                policies.append(policy)

    canonical: PolicyDocument
    if not policies:
        canonical = PolicyDocument(
            policy_id=template_id,
            name=template.name,
            version=template.version,
            owner=template.owner,
            status="active",
            language="en",
            source_url=template.source_url,
            content=template.content,
            metadata_json=_merge_master_metadata(template, template.metadata_json),
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(canonical)
        db.flush()  # assign canonical.id for duplicate handling
        stats["created"] += 1
        return canonical, stats

    canonical = max(policies, key=_sort_key_policy)

    # Ensure canonical invariants (avoid clobbering user-edited content).
    changed = False

    if (canonical.status or "").lower() != "active":
        canonical.status = "active"
        changed = True

    if canonical.policy_id != template_id:
        conflict = (
            db.query(PolicyDocument)
            .filter(PolicyDocument.policy_id == template_id, PolicyDocument.id != canonical.id)
            .first()
        )
        if not conflict:
            canonical.policy_id = template_id
            changed = True
        else:
            logger.warning(
                "Cannot set canonical policy_id to template_id due to conflict",
                extra={"template_id": template_id, "canonical_id": canonical.id, "conflict_id": conflict.id},
            )

    if not (canonical.owner or "").strip() and (template.owner or "").strip():
        canonical.owner = template.owner
        changed = True

    if not (canonical.version or "").strip() and (template.version or "").strip():
        canonical.version = template.version
        changed = True

    if not (canonical.source_url or "").strip() and (template.source_url or "").strip():
        canonical.source_url = template.source_url
        changed = True

    if not (canonical.content or "").strip() and (template.content or "").strip():
        canonical.content = template.content
        changed = True

    merged_meta = _merge_master_metadata(template, canonical.metadata_json)
    if merged_meta != (canonical.metadata_json or {}):
        canonical.metadata_json = merged_meta or None
        changed = True

    if changed:
        canonical.updated_at = utc_now()
        stats["updated"] += 1

    # Retire duplicates
    for other in policies:
        if other.id == canonical.id:
            continue
        other_changed = False
        if (other.status or "").lower() != "retired":
            other.status = "retired"
            other_changed = True
        other_meta = dict(other.metadata_json or {})
        other_meta["template_id"] = template_id
        other_meta["duplicate_of"] = canonical.id
        other_meta["is_master_policy"] = False
        if other_meta != (other.metadata_json or {}):
            other.metadata_json = other_meta or None
            other_changed = True
        if other_changed:
            other.updated_at = utc_now()
            stats["duplicates_retired"] += 1

        # If any obligations were linked to the duplicate policy, relink to canonical.
        db.query(RegulatoryObligation).filter(RegulatoryObligation.linked_policy_id == other.id).update(
            {"linked_policy_id": canonical.id, "updated_at": utc_now()}
        )

    return canonical, stats


def ensure_master_policies(db: Optional[Session] = None) -> Dict[str, int]:
    """Ensure canonical master policies exist for all active PolicyTemplates."""
    owns_session = db is None
    if db is None:
        db = SessionLocal()

    created = 0
    updated = 0
    duplicates_retired = 0

    try:
        templates = db.query(PolicyTemplate).filter(PolicyTemplate.is_active == True).all()
        if not templates:
            return {"created": 0, "updated": 0, "duplicates_retired": 0}

        # Pre-load all policies once; we'll group by template_id using Python matching.
        policies = db.query(PolicyDocument).all()
        by_template: Dict[str, List[PolicyDocument]] = {t.template_id: [] for t in templates}
        template_ids = set(by_template.keys())

        for policy in policies:
            matched_ids = set()
            if policy.policy_id in template_ids:
                matched_ids.add(policy.policy_id)
            meta_template_id = (policy.metadata_json or {}).get("template_id")
            if meta_template_id in template_ids:
                matched_ids.add(meta_template_id)
            for tid in matched_ids:
                by_template[tid].append(policy)

        for template in templates:
            _, stats = ensure_master_policy_for_template(
                db, template, existing_policies=by_template.get(template.template_id) or []
            )
            created += stats.get("created", 0)
            updated += stats.get("updated", 0)
            duplicates_retired += stats.get("duplicates_retired", 0)

        db.commit()
        return {"created": created, "updated": updated, "duplicates_retired": duplicates_retired}
    except Exception:
        if owns_session:
            db.rollback()
        raise
    finally:
        if owns_session:
            db.close()
