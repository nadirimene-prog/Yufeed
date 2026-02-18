"""Bridge between KYC lifecycle events and triageable Findings."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from src.models.finding_models import Finding
from src.services.finding_service import FindingService


class KYCFindingBridge:
    """Create normalized findings for KYC lifecycle signals."""

    def __init__(self, db: Session):
        self.db = db
        self.finding_service = FindingService(db)

    def create_kyc_failure(
        self,
        *,
        tenant_id: str,
        profile_id: int,
        user_id: Optional[str],
        reason: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Finding, bool]:
        fingerprint = f"{tenant_id}:KYC_FAILURE:{profile_id}:{reason}"
        return self.finding_service.create_or_update_finding(
            tenant_id=tenant_id,
            finding_type="KYC_FAILURE",
            fingerprint=fingerprint,
            severity="high",
            title="KYC verification failure",
            summary=reason,
            source_refs={
                "profile_id": profile_id,
                "user_id": user_id,
                "domain": "kyc",
            },
            explainability=details or {},
        )

    def create_onboarding_risk(
        self,
        *,
        tenant_id: str,
        profile_id: int,
        user_id: Optional[str],
        summary: str,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "medium",
    ) -> Tuple[Finding, bool]:
        fingerprint = f"{tenant_id}:ONBOARDING_RISK:{profile_id}:{summary}"
        return self.finding_service.create_or_update_finding(
            tenant_id=tenant_id,
            finding_type="ONBOARDING_RISK",
            fingerprint=fingerprint,
            severity=severity,
            title="Onboarding risk signal",
            summary=summary,
            source_refs={
                "profile_id": profile_id,
                "user_id": user_id,
                "domain": "kyc",
            },
            explainability=details or {},
        )

    def create_kyc_expiry(
        self,
        *,
        tenant_id: str,
        profile_id: int,
        user_id: Optional[str],
        summary: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Finding, bool]:
        fingerprint = f"{tenant_id}:KYC_EXPIRY:{profile_id}:{summary}"
        return self.finding_service.create_or_update_finding(
            tenant_id=tenant_id,
            finding_type="KYC_EXPIRY",
            fingerprint=fingerprint,
            severity="medium",
            title="KYC review or document expiry",
            summary=summary,
            source_refs={
                "profile_id": profile_id,
                "user_id": user_id,
                "domain": "kyc",
            },
            explainability=details or {},
        )

    def create_edd_trigger(
        self,
        *,
        tenant_id: str,
        profile_id: int,
        user_id: Optional[str],
        reason: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Finding, bool]:
        fingerprint = f"{tenant_id}:EDD_TRIGGER:{profile_id}:{reason}"
        return self.finding_service.create_or_update_finding(
            tenant_id=tenant_id,
            finding_type="EDD_TRIGGER",
            fingerprint=fingerprint,
            severity="high",
            title="EDD escalation required",
            summary=reason,
            source_refs={
                "profile_id": profile_id,
                "user_id": user_id,
                "domain": "kyc",
            },
            explainability=details or {},
        )
