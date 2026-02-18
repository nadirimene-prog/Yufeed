"""KYC onboarding lifecycle service."""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from src.integrations.sanctions.service import SanctionsService
from src.models.compliance import (
    ComplianceDocument,
    ComplianceProfile,
    ComplianceStatus,
    KYCProfile,
    RiskSignal,
)
from src.models.transaction_models import UserRiskProfile
from src.plugins.kyc_vendor import KYCVendorPlugin
from src.services.kyc_finding_bridge import KYCFindingBridge
from src.services.sanctions_finding_bridge import create_findings_from_screening
from src.tenancy.context import get_current_tenant

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class KYCOnboardingService:
    """Coordinates KYC profile lifecycle operations."""

    def __init__(self, db: Session):
        self.db = db
        self.finding_bridge = KYCFindingBridge(db)

    def initiate_onboarding(
        self,
        profile_id: int,
        *,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        profile = self._get_profile(profile_id=profile_id, tenant_id=tenant_id)
        if user_id and not profile.user_id:
            profile.user_id = user_id
        if not profile.review_frequency_months:
            profile.review_frequency_months = self._review_frequency_months(profile.cdd_level)
        if not profile.next_review_date:
            profile.next_review_date = self._calculate_next_review_date(
                profile.cdd_level, profile.review_frequency_months
            )
        profile.status = ComplianceStatus.PENDING.value

        screening = self.screen_customer(profile_id=profile.id, tenant_id=profile.tenant_id)
        level = self.determine_cdd_level(profile.id, tenant_id=profile.tenant_id)
        self.db.flush()
        return {
            "profile_id": profile.id,
            "tenant_id": profile.tenant_id,
            "status": profile.status,
            "screening": screening,
            "cdd_level": level,
        }

    def screen_customer(
        self, profile_id: int, *, tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        profile = self._get_profile(profile_id=profile_id, tenant_id=tenant_id)
        screening_result = self._run_async(self._screen_profile(profile))

        profile.sanctions_screened_at = utc_now()
        profile.sanctions_status = "hit" if screening_result.is_hit else "clear"

        findings = create_findings_from_screening(
            self.db,
            tenant_id=profile.tenant_id,
            screening_result=screening_result,
            subject_type="kyc_profile",
            subject_id=str(profile.id),
        )

        findings_created = len(findings)
        if screening_result.is_hit:
            self.finding_bridge.create_onboarding_risk(
                tenant_id=profile.tenant_id,
                profile_id=profile.id,
                user_id=profile.user_id,
                summary="Sanctions screening produced one or more matches",
                details={
                    "highest_score": screening_result.highest_score,
                    "match_count": len(screening_result.matches),
                },
                severity="high",
            )
            findings_created += 1

        self.db.flush()
        return {
            "profile_id": profile.id,
            "sanctions_status": profile.sanctions_status,
            "screened_at": profile.sanctions_screened_at,
            "is_hit": screening_result.is_hit,
            "highest_score": screening_result.highest_score,
            "match_count": len(screening_result.matches),
            "findings_created": findings_created,
        }

    def verify_documents(
        self,
        profile_id: int,
        *,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        profile = self._get_profile(profile_id=profile_id, tenant_id=tenant_id)
        docs = (
            self.db.query(ComplianceDocument)
            .filter(
                ComplianceDocument.profile_id == profile.id,
                ComplianceDocument.tenant_id == profile.tenant_id,
            )
            .all()
        )

        verified_count = 0
        rejected_count = 0
        error_count = 0
        findings_created = 0

        for doc in docs:
            verification = self._run_async(
                self._verify_document(profile=profile, document=doc, tenant_id=profile.tenant_id)
            )
            status = str(verification.get("status", "unknown")).lower()
            doc.vendor_response = verification
            doc.vendor_verification_id = str(verification.get("verification_id") or "") or None

            if status in {"verified", "approved", "passed", "clear"}:
                doc.verification_status = "verified"
                doc.verified_at = utc_now()
                doc.verified_by = "system:kyc_vendor"
                doc.rejection_reason = None
                verified_count += 1
                continue

            if status in {"rejected", "failed", "declined"}:
                doc.verification_status = "rejected"
                doc.verified_at = utc_now()
                doc.verified_by = "system:kyc_vendor"
                reason = self._normalize_rejection_reason(verification)
                doc.rejection_reason = reason
                rejected_count += 1
                self.finding_bridge.create_kyc_failure(
                    tenant_id=profile.tenant_id,
                    profile_id=profile.id,
                    user_id=profile.user_id,
                    reason=f"Document {doc.document_type} rejected",
                    details={"document_id": doc.id, "reason": reason},
                )
                findings_created += 1
                continue

            if status == "error":
                doc.verification_status = "error"
                doc.verified_by = "system:kyc_vendor"
                doc.rejection_reason = verification.get("error") or "Vendor verification error"
                error_count += 1
                self.finding_bridge.create_kyc_failure(
                    tenant_id=profile.tenant_id,
                    profile_id=profile.id,
                    user_id=profile.user_id,
                    reason=f"Document {doc.document_type} verification error",
                    details={
                        "document_id": doc.id,
                        "error": verification.get("error"),
                    },
                )
                findings_created += 1
                continue

            doc.verification_status = "pending"

        self.db.flush()
        return {
            "profile_id": profile.id,
            "processed_count": len(docs),
            "verified_count": verified_count,
            "rejected_count": rejected_count,
            "error_count": error_count,
            "findings_created": findings_created,
            "documents": docs,
        }

    def determine_cdd_level(
        self,
        profile_id: int,
        *,
        tenant_id: Optional[str] = None,
        requested_level: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> str:
        profile = self._get_profile(profile_id=profile_id, tenant_id=tenant_id)
        previous_level = (profile.cdd_level or "standard").lower()

        if requested_level:
            level = requested_level.lower().strip()
        else:
            level, inferred_reason = self._infer_cdd_level(profile)
            if not reason:
                reason = inferred_reason

        if level not in {"simplified", "standard", "enhanced"}:
            level = "standard"

        profile.cdd_level = level
        profile.cdd_reason = reason
        profile.review_frequency_months = self._review_frequency_months(level)
        profile.next_review_date = self._calculate_next_review_date(
            level, profile.review_frequency_months
        )

        if previous_level != "enhanced" and level == "enhanced":
            self.finding_bridge.create_edd_trigger(
                tenant_id=profile.tenant_id,
                profile_id=profile.id,
                user_id=profile.user_id,
                reason=reason or "CDD escalated to enhanced",
                details={"previous_level": previous_level, "current_level": level},
            )

        self.db.flush()
        return level

    def approve_onboarding(
        self,
        profile_id: int,
        *,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> ComplianceProfile:
        profile = self._get_profile(profile_id=profile_id, tenant_id=tenant_id)
        if user_id:
            profile.user_id = user_id

        profile.status = ComplianceStatus.APPROVED.value
        profile.last_review_date = utc_now()

        if profile.user_id:
            risk_profile = (
                self.db.query(UserRiskProfile)
                .filter(
                    UserRiskProfile.tenant_id == profile.tenant_id,
                    UserRiskProfile.user_id == profile.user_id,
                )
                .first()
            )
            if not risk_profile:
                risk_profile = UserRiskProfile(
                    tenant_id=profile.tenant_id,
                    user_id=profile.user_id,
                )
                self.db.add(risk_profile)

            risk_profile.kyc_status = profile.status
            risk_profile.kyc_last_updated = utc_now()
            risk_profile.enhanced_due_diligence = profile.cdd_level == "enhanced"
            risk_profile.sanctions_screened_at = profile.sanctions_screened_at
            risk_profile.sanctions_match = profile.sanctions_status == "hit"
            risk_profile.sanctions_details = {
                "pep_status": profile.pep_status,
                "sanctions_status": profile.sanctions_status,
                "cdd_level": profile.cdd_level,
            }

        self.db.flush()
        return profile

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

    def _infer_cdd_level(self, profile: KYCProfile) -> Tuple[str, str]:
        signals: List[RiskSignal] = (
            self.db.query(RiskSignal)
            .filter(
                RiskSignal.profile_id == profile.id,
                RiskSignal.tenant_id == profile.tenant_id,
            )
            .all()
        )
        max_signal_score = max((int(signal.score or 0) for signal in signals), default=0)

        pep_status = (profile.pep_status or "unknown").lower()
        sanctions_status = (profile.sanctions_status or "").lower()

        if pep_status in {"pep", "rca"}:
            return "enhanced", "PEP/RCA status requires enhanced due diligence"
        if sanctions_status == "hit":
            return "enhanced", "Sanctions hit requires enhanced due diligence"
        if max_signal_score >= 70:
            return "enhanced", "High risk signals require enhanced due diligence"

        if (
            (profile.risk_level or "").lower() == "low"
            and max_signal_score <= 20
            and sanctions_status in {"", "clear"}
            and pep_status in {"not_pep", "unknown"}
        ):
            return "simplified", "Low-risk profile qualifies for simplified due diligence"

        return "standard", "Default standard due diligence"

    @staticmethod
    def _review_frequency_months(level: Optional[str]) -> int:
        normalized = (level or "standard").lower()
        if normalized == "enhanced":
            return 6
        if normalized == "simplified":
            return 24
        return 12

    @staticmethod
    def _calculate_next_review_date(level: Optional[str], months: Optional[int]) -> datetime:
        months_value = months or KYCOnboardingService._review_frequency_months(level)
        return utc_now() + timedelta(days=months_value * 30)

    @staticmethod
    def _normalize_rejection_reason(verification: Dict[str, Any]) -> str:
        flags = verification.get("flags") or []
        if isinstance(flags, list) and flags:
            return ", ".join(str(flag) for flag in flags)
        return "Document verification rejected"

    @staticmethod
    async def _screen_profile(profile: KYCProfile):
        sanctions_service = SanctionsService()
        await sanctions_service.initialize()
        screened_name = f"{profile.first_name} {profile.last_name}".strip()
        return await sanctions_service.screen_name(screened_name)

    @staticmethod
    async def _verify_document(
        *,
        profile: KYCProfile,
        document: ComplianceDocument,
        tenant_id: str,
    ) -> Dict[str, Any]:
        plugin = KYCVendorPlugin()
        external_user_id = profile.user_id or f"{tenant_id}:{profile.id}:{document.id}"
        result = await plugin.verify_user(external_user_id)
        return result

    @staticmethod
    def _run_async(coro):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        if loop.is_running():
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(lambda: asyncio.run(coro))
                return future.result()

        return loop.run_until_complete(coro)
