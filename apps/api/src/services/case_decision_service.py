"""CaseDecision service — state machine + 4-eyes approval.

Handles the governance workflow for compliance decisions on investigation
cases.  Transitions: draft → submitted → approved / rejected.
"""

import logging
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.audit.recorders import record_event, record_decision
from src.models.case_decision import CaseDecision, CaseDecisionStatus
from src.models.transaction_models import Case
from src.utils.time import utc_now

logger = logging.getLogger(__name__)


class CaseDecisionService:
    """Manages Case Decision lifecycle with state validation."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Create (draft)
    # ------------------------------------------------------------------

    def create_decision(
        self,
        case_id: int,
        tenant_id: str,
        disposition: str,
        rationale: Optional[str],
        created_by: str,
    ) -> CaseDecision:
        """Create a new draft decision for a case.

        Auto-increments ``version`` based on existing decisions.
        """
        # Verify case exists and belongs to tenant
        case = self.db.query(Case).filter(Case.id == case_id, Case.tenant_id == tenant_id).first()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        # Auto-increment version
        latest_version = (
            self.db.query(func.max(CaseDecision.version))
            .filter(CaseDecision.case_id == case_id, CaseDecision.tenant_id == tenant_id)
            .scalar()
        ) or 0

        decision = CaseDecision(
            tenant_id=tenant_id,
            case_id=case_id,
            version=latest_version + 1,
            status=CaseDecisionStatus.draft.value,
            disposition=disposition,
            rationale=rationale,
            created_by=created_by,
        )
        self.db.add(decision)
        self.db.flush()

        record_event(
            self.db,
            event_type="decision.created",
            entity_type="case_decision",
            entity_id=str(decision.id),
            tenant_id=tenant_id,
            payload={
                "case_id": case.case_id,
                "disposition": disposition,
                "version": decision.version,
            },
        )
        logger.info(
            "Created decision id=%s case=%s v=%s",
            decision.id,
            case.case_id,
            decision.version,
        )
        return decision

    # ------------------------------------------------------------------
    # Submit
    # ------------------------------------------------------------------

    def submit_decision(
        self,
        decision_id: int,
        tenant_id: str,
        rationale: str,
        actor_id: str,
        case_id: Optional[int] = None,
    ) -> CaseDecision:
        """Transition a decision from draft → submitted."""
        decision = self._get_decision(decision_id, tenant_id, case_id=case_id)
        self._assert_transition(decision, CaseDecisionStatus.draft, CaseDecisionStatus.submitted)

        decision.status = CaseDecisionStatus.submitted.value
        decision.rationale = rationale
        decision.submitted_at = utc_now()
        decision.updated_at = utc_now()

        # Move case to decision_pending
        case = decision.case
        if case:
            case.status = "decision_pending"
            case.updated_at = utc_now()

        record_event(
            self.db,
            event_type="decision.submitted",
            entity_type="case_decision",
            entity_id=str(decision.id),
            tenant_id=tenant_id,
            payload={"actor": actor_id, "disposition": decision.disposition},
        )
        logger.info("Submitted decision id=%s", decision.id)
        return decision

    # ------------------------------------------------------------------
    # Approve (4-eyes)
    # ------------------------------------------------------------------

    def approve_decision(
        self,
        decision_id: int,
        tenant_id: str,
        approver_id: str,
        comment: Optional[str] = None,
        case_id: Optional[int] = None,
    ) -> CaseDecision:
        """Approve a submitted decision.

        Enforces 4-eyes: ``approver_id`` must differ from ``created_by``.
        On approval the parent Case is auto-closed.
        """
        decision = self._get_decision(decision_id, tenant_id, case_id=case_id)
        self._assert_transition(decision, CaseDecisionStatus.submitted, CaseDecisionStatus.approved)

        if approver_id == decision.created_by:
            raise HTTPException(
                status_code=409,
                detail="4-eyes violation: approver cannot be the same as the decision creator",
            )

        decision.status = CaseDecisionStatus.approved.value
        decision.approver_id = approver_id
        decision.approved_at = utc_now()
        decision.updated_at = utc_now()

        # Auto-close the case
        case = decision.case
        if case:
            case.status = "closed"
            case.outcome = decision.disposition
            case.outcome_notes = decision.rationale
            case.closed_at = utc_now()
            case.updated_at = utc_now()

        # Audit events
        event_record = record_event(
            self.db,
            event_type="decision.approved",
            entity_type="case_decision",
            entity_id=str(decision.id),
            tenant_id=tenant_id,
            payload={
                "approver": approver_id,
                "disposition": decision.disposition,
                "case_id": case.case_id if case else None,
                "comment": comment,
            },
        )
        # Also write to the immutable DecisionRecord for compliance
        record_decision(
            self.db,
            decision=decision.disposition,
            tenant_id=tenant_id,
            event_id=event_record.event_id,
            reason_codes=[decision.disposition],
            evidence={
                "rationale": decision.rationale,
                "approver": approver_id,
                "case_decision_id": decision.id,
                "case_decision_version": decision.version,
            },
        )
        logger.info("Approved decision id=%s by %s", decision.id, approver_id)
        return decision

    # ------------------------------------------------------------------
    # Reject
    # ------------------------------------------------------------------

    def reject_decision(
        self,
        decision_id: int,
        tenant_id: str,
        rejector_id: str,
        rejection_reason: str,
        case_id: Optional[int] = None,
    ) -> CaseDecision:
        """Reject a submitted decision.  Case remains open/investigating."""
        decision = self._get_decision(decision_id, tenant_id, case_id=case_id)
        self._assert_transition(decision, CaseDecisionStatus.submitted, CaseDecisionStatus.rejected)

        decision.status = CaseDecisionStatus.rejected.value
        decision.approver_id = rejector_id
        decision.rejection_reason = rejection_reason
        decision.updated_at = utc_now()

        # Move case back to investigating (from decision_pending)
        case = decision.case
        if case and case.status == "decision_pending":
            case.status = "in_progress"
            case.updated_at = utc_now()

        record_event(
            self.db,
            event_type="decision.rejected",
            entity_type="case_decision",
            entity_id=str(decision.id),
            tenant_id=tenant_id,
            payload={
                "rejector": rejector_id,
                "reason": rejection_reason,
            },
        )
        logger.info("Rejected decision id=%s by %s", decision.id, rejector_id)
        return decision

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_decision(
        self, decision_id: int, tenant_id: str, case_id: Optional[int] = None
    ) -> CaseDecision:
        q = self.db.query(CaseDecision).filter(
            CaseDecision.id == decision_id,
            CaseDecision.tenant_id == tenant_id,
        )
        if case_id is not None:
            q = q.filter(CaseDecision.case_id == case_id)
        decision = q.first()
        if not decision:
            raise HTTPException(status_code=404, detail="Decision not found")
        return decision

    @staticmethod
    def _assert_transition(
        decision: CaseDecision,
        expected_from: CaseDecisionStatus,
        target: CaseDecisionStatus,
    ) -> None:
        if decision.status != expected_from.value:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Invalid transition: cannot move from '{decision.status}' "
                    f"to '{target.value}' (expected '{expected_from.value}')"
                ),
            )
