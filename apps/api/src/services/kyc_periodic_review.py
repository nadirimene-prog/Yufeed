"""Periodic KYC review service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from src.models.compliance import (
    ComplianceDocument,
    ComplianceProfile,
    ComplianceStatus,
    KYCProfile,
)
from src.tenancy.context import get_current_tenant


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class KYCPeriodicReviewService:
    """Schedules and manages periodic KYC re-assessments."""

    def __init__(self, db: Session):
        self.db = db

    def find_profiles_due_for_review(
        self,
        *,
        tenant_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[KYCProfile]:
        now = utc_now()
        resolved_tenant = tenant_id or get_current_tenant()

        query = self.db.query(KYCProfile).filter(KYCProfile.type == "kyc")
        if resolved_tenant:
            query = query.filter(KYCProfile.tenant_id == resolved_tenant)

        query = query.filter(
            and_(
                KYCProfile.status.in_(
                    [
                        ComplianceStatus.APPROVED.value,
                        ComplianceStatus.MANUAL_REVIEW.value,
                    ]
                ),
                or_(
                    KYCProfile.next_review_date.is_(None),
                    KYCProfile.next_review_date <= now,
                ),
            )
        )
        return query.order_by(KYCProfile.next_review_date.asc()).limit(limit).all()

    def initiate_review(
        self,
        profile_id: int,
        *,
        tenant_id: Optional[str] = None,
    ) -> KYCProfile:
        profile = self._get_profile(profile_id=profile_id, tenant_id=tenant_id)
        profile.status = ComplianceStatus.MANUAL_REVIEW.value
        profile.last_review_date = utc_now()
        self.db.flush()
        return profile

    def complete_review(
        self,
        profile_id: int,
        *,
        tenant_id: Optional[str] = None,
        approved: bool = True,
    ) -> KYCProfile:
        profile = self._get_profile(profile_id=profile_id, tenant_id=tenant_id)
        profile.status = (
            ComplianceStatus.APPROVED.value if approved else ComplianceStatus.REJECTED.value
        )
        profile.last_review_date = utc_now()
        months = int(profile.review_frequency_months or 12)
        profile.next_review_date = utc_now() + timedelta(days=months * 30)
        self.db.flush()
        return profile

    def find_documents_expiring_in(
        self,
        *,
        tenant_id: Optional[str] = None,
        days: int = 30,
    ) -> List[ComplianceDocument]:
        now = utc_now()
        cutoff = now + timedelta(days=days)
        resolved_tenant = tenant_id or get_current_tenant()

        query = self.db.query(ComplianceDocument).filter(
            ComplianceDocument.expiry_date.is_not(None),
            ComplianceDocument.expiry_date <= cutoff,
            ComplianceDocument.expiry_date >= now,
        )
        if resolved_tenant:
            query = query.filter(ComplianceDocument.tenant_id == resolved_tenant)
        return query.order_by(ComplianceDocument.expiry_date.asc()).all()

    def _get_profile(self, *, profile_id: int, tenant_id: Optional[str]) -> KYCProfile:
        resolved_tenant = tenant_id or get_current_tenant() or "default"
        profile = (
            self.db.query(KYCProfile)
            .filter(
                KYCProfile.id == profile_id,
                KYCProfile.tenant_id == resolved_tenant,
            )
            .first()
        )
        if not profile:
            raise ValueError("KYC profile not found")
        return profile
