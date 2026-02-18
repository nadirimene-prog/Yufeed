"""
Tenant-level regulatory applicability service.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.orm import Session

from src.compliance.scope import normalize_scopes
from src.models.models import LegalDocument
from src.models.tenant_models import Tenant, TenantRegulatoryProfile


VALID_INSTITUTION_TYPES = {"pi", "emi", "vasp", "credit_institution"}
VALID_APPLICABILITY = {"full", "partial", "exempt"}

INSTITUTION_SCOPE_MAP = {
    "pi": ["psp"],
    "emi": ["psp", "eme"],
    "vasp": ["vasp"],
    "credit_institution": ["psp"],
}

INSTITUTION_TYPE_ALIASES = {
    "payment_institution": "pi",
    "payment-service-provider": "pi",
    "psp": "pi",
    "electronic_money_institution": "emi",
    "electronic-money-institution": "emi",
    "casp": "vasp",
}


def _normalize_scope_list(value: Optional[Any]) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return normalize_scopes(value)
    if isinstance(value, list):
        tags: List[str] = []
        for item in value:
            if not isinstance(item, str):
                continue
            canonical = normalize_scopes(item)
            for tag in canonical:
                if tag not in tags:
                    tags.append(tag)
        return tags
    return []


def _date_sort_key(doc: LegalDocument) -> tuple:
    publication_date = doc.publication_date.isoformat() if doc.publication_date else ""
    return (publication_date, doc.id)


class TenantComplianceService:
    @staticmethod
    def normalize_institution_type(raw_value: Optional[str]) -> Optional[str]:
        if raw_value is None:
            return None

        normalized = raw_value.strip().lower()
        if not normalized:
            return None
        return INSTITUTION_TYPE_ALIASES.get(normalized, normalized)

    @classmethod
    def validate_institution_type(cls, value: Optional[str]) -> Optional[str]:
        normalized = cls.normalize_institution_type(value)
        if normalized is None:
            return None
        if normalized not in VALID_INSTITUTION_TYPES:
            allowed = ", ".join(sorted(VALID_INSTITUTION_TYPES))
            raise ValueError(f"institution_type must be one of: {allowed}")
        return normalized

    @staticmethod
    def validate_applicability(value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in VALID_APPLICABILITY:
            allowed = ", ".join(sorted(VALID_APPLICABILITY))
            raise ValueError(f"applicability must be one of: {allowed}")
        return normalized

    @classmethod
    def derive_scope_tags(
        cls,
        institution_type: Optional[str],
        explicit_scope_tags: Optional[Any],
    ) -> List[str]:
        explicit = _normalize_scope_list(explicit_scope_tags)
        if explicit:
            return explicit

        normalized_type = cls.normalize_institution_type(institution_type)
        if not normalized_type:
            return []
        return INSTITUTION_SCOPE_MAP.get(normalized_type, [])

    @classmethod
    def get_applicable_regulations(
        cls,
        db: Session,
        tenant: Tenant,
        include_exempt: bool = False,
    ) -> List[Dict[str, Any]]:
        tenant_scope_tags = cls.derive_scope_tags(
            institution_type=tenant.institution_type,
            explicit_scope_tags=tenant.regulatory_scope_tags,
        )
        tenant_scopes: Set[str] = set(tenant_scope_tags)

        explicit_rows = (
            db.query(TenantRegulatoryProfile)
            .filter(TenantRegulatoryProfile.tenant_id == tenant.id)
            .all()
        )
        explicit_by_doc = {row.regulation_doc_id: row for row in explicit_rows}

        docs = db.query(LegalDocument).all()
        docs_sorted = sorted(docs, key=_date_sort_key, reverse=True)

        applicable: List[Dict[str, Any]] = []
        for doc in docs_sorted:
            explicit = explicit_by_doc.get(doc.id)
            doc_scope_tags = _normalize_scope_list(doc.scope_tags)
            doc_scopes: Set[str] = set(doc_scope_tags)

            inferred_applicable = not doc_scopes or bool(doc_scopes.intersection(tenant_scopes))
            applicability = "full" if inferred_applicable else "not_applicable"
            applicability_source = "inferred"
            applicability_notes = None
            effective_from = None

            if explicit:
                applicability = explicit.applicability
                applicability_source = "manual_override"
                applicability_notes = explicit.applicability_notes
                effective_from = explicit.effective_from

            if applicability == "exempt" and not include_exempt:
                continue
            if applicability == "not_applicable":
                continue

            applicable.append(
                {
                    "regulation_doc_id": doc.id,
                    "celex": doc.celex,
                    "title": doc.title,
                    "publication_date": doc.publication_date,
                    "scope_tags": doc_scope_tags,
                    "applicability": applicability,
                    "applicability_source": applicability_source,
                    "applicability_notes": applicability_notes,
                    "effective_from": effective_from,
                }
            )

        return applicable

    @classmethod
    def upsert_regulation_override(
        cls,
        db: Session,
        tenant: Tenant,
        regulation_doc_id: int,
        applicability: str,
        applicability_notes: Optional[str],
        effective_from: Optional[datetime],
        actor_user_id: Optional[str],
    ) -> tuple[TenantRegulatoryProfile, bool]:
        normalized_applicability = cls.validate_applicability(applicability)
        existing = (
            db.query(TenantRegulatoryProfile)
            .filter(
                TenantRegulatoryProfile.tenant_id == tenant.id,
                TenantRegulatoryProfile.regulation_doc_id == regulation_doc_id,
            )
            .first()
        )

        created = False
        if existing is None:
            existing = TenantRegulatoryProfile(
                tenant_id=tenant.id,
                regulation_doc_id=regulation_doc_id,
                created_by=actor_user_id,
            )
            db.add(existing)
            created = True

        existing.applicability = normalized_applicability
        existing.applicability_notes = applicability_notes
        existing.effective_from = effective_from

        return existing, created
