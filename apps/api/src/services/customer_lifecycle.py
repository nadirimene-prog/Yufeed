"""Customer lifecycle bridge between KYC and transaction monitoring."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from src.models.compliance import ComplianceProfile
from src.models.transaction_models import Transaction, UserRiskProfile
from src.services.kyc_finding_bridge import KYCFindingBridge


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CustomerLifecycleService:
    """Synchronize KYC into risk profile and trigger EDD from transaction patterns."""

    def __init__(self, db: Session):
        self.db = db
        self.kyc_finding_bridge = KYCFindingBridge(db)

    def sync_kyc_to_risk_profile(self, user_id: str, tenant_id: str) -> Optional[UserRiskProfile]:
        compliance_profile = (
            self.db.query(ComplianceProfile)
            .filter(
                ComplianceProfile.tenant_id == tenant_id,
                ComplianceProfile.user_id == user_id,
            )
            .order_by(ComplianceProfile.updated_at.desc(), ComplianceProfile.id.desc())
            .first()
        )
        if not compliance_profile:
            return None

        risk_profile = (
            self.db.query(UserRiskProfile)
            .filter(
                UserRiskProfile.tenant_id == tenant_id,
                UserRiskProfile.user_id == user_id,
            )
            .first()
        )
        if not risk_profile:
            risk_profile = UserRiskProfile(tenant_id=tenant_id, user_id=user_id)
            self.db.add(risk_profile)
            self.db.flush()

        risk_profile.compliance_profile_id = compliance_profile.id
        risk_profile.kyc_status = compliance_profile.status
        risk_profile.kyc_cdd_level = compliance_profile.cdd_level
        risk_profile.kyc_pep_status = compliance_profile.pep_status
        risk_profile.kyc_last_synced_at = utc_now()
        risk_profile.kyc_last_updated = compliance_profile.updated_at or utc_now()
        risk_profile.kyc_risk_score = self._compute_kyc_risk_score(compliance_profile)
        risk_profile.enhanced_due_diligence = (
            str(compliance_profile.cdd_level or "").lower() == "enhanced"
        )
        risk_profile.sanctions_screened_at = compliance_profile.sanctions_screened_at
        risk_profile.sanctions_match = (
            str(compliance_profile.sanctions_status or "").lower() == "hit"
        )

        sanctions_details = dict(risk_profile.sanctions_details or {})
        sanctions_details.update(
            {
                "kyc_profile_id": compliance_profile.id,
                "sanctions_status": compliance_profile.sanctions_status,
                "pep_status": compliance_profile.pep_status,
                "cdd_level": compliance_profile.cdd_level,
            }
        )
        risk_profile.sanctions_details = sanctions_details
        return risk_profile

    def trigger_edd_from_transactions(
        self, transaction_db_id: int, tenant_id: str
    ) -> Dict[str, Any]:
        transaction = (
            self.db.query(Transaction)
            .filter(
                Transaction.id == transaction_db_id,
                Transaction.tenant_id == tenant_id,
            )
            .first()
        )
        if not transaction:
            return {"triggered": False, "reason": "transaction_not_found"}

        risk_profile = (
            self.db.query(UserRiskProfile)
            .filter(
                UserRiskProfile.tenant_id == tenant_id,
                UserRiskProfile.user_id == transaction.user_id,
            )
            .first()
        )
        if not risk_profile:
            return {"triggered": False, "reason": "risk_profile_not_found"}

        reasons = []
        tx_risk_score = float(transaction.risk_score or 0)
        tx_amount = float(transaction.amount or 0)
        tx_risk_level = str(transaction.risk_level or "").lower()
        kyc_status = str(risk_profile.kyc_status or "").lower()

        if tx_risk_score >= 80:
            reasons.append("high_transaction_risk_score")
        if tx_risk_level in {"high", "critical"}:
            reasons.append("high_transaction_risk_level")
        if tx_amount >= 10000 and kyc_status != "approved":
            reasons.append("high_value_without_approved_kyc")

        if not reasons:
            return {"triggered": False, "reason": "no_edd_trigger_conditions"}

        risk_profile.enhanced_due_diligence = True

        compliance_profile = None
        if risk_profile.compliance_profile_id:
            compliance_profile = (
                self.db.query(ComplianceProfile)
                .filter(
                    ComplianceProfile.id == risk_profile.compliance_profile_id,
                    ComplianceProfile.tenant_id == tenant_id,
                )
                .first()
            )

        if compliance_profile:
            compliance_profile.cdd_level = "enhanced"
            compliance_profile.cdd_reason = "Triggered by transaction monitoring patterns"

        finding, _is_new = self.kyc_finding_bridge.create_edd_trigger(
            tenant_id=tenant_id,
            profile_id=compliance_profile.id if compliance_profile else 0,
            user_id=transaction.user_id,
            reason=";".join(reasons),
            details={
                "transaction_id": transaction.transaction_id,
                "transaction_db_id": transaction.id,
                "risk_score": tx_risk_score,
                "risk_level": tx_risk_level,
                "amount": tx_amount,
            },
        )
        return {
            "triggered": True,
            "reason": ";".join(reasons),
            "finding_id": finding.id,
        }

    def check_kyc_for_transaction(self, transaction_db_id: int, tenant_id: str) -> Dict[str, Any]:
        transaction = (
            self.db.query(Transaction)
            .filter(
                Transaction.id == transaction_db_id,
                Transaction.tenant_id == tenant_id,
            )
            .first()
        )
        if not transaction:
            return {"is_compliant": False, "reason": "transaction_not_found"}

        compliance_profile = (
            self.db.query(ComplianceProfile)
            .filter(
                ComplianceProfile.tenant_id == tenant_id,
                ComplianceProfile.user_id == transaction.user_id,
            )
            .order_by(ComplianceProfile.updated_at.desc(), ComplianceProfile.id.desc())
            .first()
        )
        if not compliance_profile:
            return {"is_compliant": False, "reason": "kyc_profile_not_found"}

        if str(compliance_profile.status or "").lower() != "approved":
            return {
                "is_compliant": False,
                "reason": "kyc_not_approved",
                "status": compliance_profile.status,
            }

        return {"is_compliant": True, "reason": "ok", "status": compliance_profile.status}

    @staticmethod
    def _compute_kyc_risk_score(compliance_profile: ComplianceProfile) -> Decimal:
        score = Decimal("0")
        if str(compliance_profile.cdd_level or "").lower() == "enhanced":
            score += Decimal("10")
        if str(compliance_profile.pep_status or "").lower() in {"pep", "rca"}:
            score += Decimal("15")
        if str(compliance_profile.status or "").lower() != "approved":
            score += Decimal("5")
        return min(Decimal("30"), score)
