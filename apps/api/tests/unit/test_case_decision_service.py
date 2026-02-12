"""Unit tests for CaseDecisionService — state machine, 4-eyes, case lifecycle."""

import pytest
from fastapi import HTTPException

from src.models.case_decision import CaseDecision, CaseDecisionStatus
from src.models.transaction_models import Case
from src.services.case_decision_service import CaseDecisionService
from src.audit.models import EventRecord, DecisionRecord
from src.tenancy.context import set_current_tenant, clear_current_tenant
from tests.factories import CaseFactory


TENANT = "default"


@pytest.fixture(autouse=True)
def _tenant_ctx():
    set_current_tenant(TENANT)
    yield
    clear_current_tenant()


def _make_case(db_session, status="open") -> Case:
    """Create an open investigation case for testing."""
    case = CaseFactory(
        sqlalchemy_session=db_session,
        tenant_id=TENANT,
        status=status,
        case_type="investigation",
        subject_type="user",
        subject_id="user_test",
        priority="medium",
        title="Test case for decisions",
    )
    return case


# ------------------------------------------------------------------
# create_decision — draft
# ------------------------------------------------------------------


@pytest.mark.unit
def test_create_draft_decision(db_session):
    """Creating a decision produces a draft with version=1."""
    case = _make_case(db_session)
    svc = CaseDecisionService(db_session)

    decision = svc.create_decision(
        case_id=case.id,
        tenant_id=TENANT,
        disposition="no_action",
        rationale="Initial assessment",
        created_by="analyst@example.com",
    )
    db_session.commit()

    assert decision.id is not None
    assert decision.version == 1
    assert decision.status == CaseDecisionStatus.draft.value
    assert decision.disposition == "no_action"
    assert decision.rationale == "Initial assessment"
    assert decision.created_by == "analyst@example.com"
    assert decision.submitted_at is None
    assert decision.approver_id is None

    # Audit event
    event = (
        db_session.query(EventRecord)
        .filter(
            EventRecord.event_type == "decision.created",
            EventRecord.entity_id == str(decision.id),
        )
        .first()
    )
    assert event is not None
    assert event.payload["disposition"] == "no_action"


@pytest.mark.unit
def test_create_decision_auto_increments_version(db_session):
    """Second decision for the same case gets version=2."""
    case = _make_case(db_session)
    svc = CaseDecisionService(db_session)

    d1 = svc.create_decision(
        case_id=case.id,
        tenant_id=TENANT,
        disposition="monitor",
        rationale="v1",
        created_by="user_a",
    )
    db_session.commit()

    d2 = svc.create_decision(
        case_id=case.id,
        tenant_id=TENANT,
        disposition="remediate",
        rationale="v2",
        created_by="user_b",
    )
    db_session.commit()

    assert d1.version == 1
    assert d2.version == 2


@pytest.mark.unit
def test_create_decision_case_not_found(db_session):
    """404 if the case doesn't exist."""
    svc = CaseDecisionService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        svc.create_decision(
            case_id=999999,
            tenant_id=TENANT,
            disposition="no_action",
            rationale="test",
            created_by="user_x",
        )
    assert exc_info.value.status_code == 404


# ------------------------------------------------------------------
# submit_decision
# ------------------------------------------------------------------


@pytest.mark.unit
def test_submit_decision(db_session):
    """Submitting moves draft → submitted and case → decision_pending."""
    case = _make_case(db_session)
    svc = CaseDecisionService(db_session)

    decision = svc.create_decision(
        case_id=case.id,
        tenant_id=TENANT,
        disposition="sar_required",
        rationale=None,
        created_by="analyst@example.com",
    )
    db_session.commit()

    submitted = svc.submit_decision(
        decision_id=decision.id,
        tenant_id=TENANT,
        rationale="After thorough review, SAR filing is required.",
        actor_id="analyst@example.com",
    )
    db_session.commit()

    assert submitted.status == CaseDecisionStatus.submitted.value
    assert submitted.rationale == "After thorough review, SAR filing is required."
    assert submitted.submitted_at is not None

    # Case should be decision_pending
    db_session.refresh(case)
    assert case.status == "decision_pending"


@pytest.mark.unit
def test_submit_from_non_draft_fails(db_session):
    """Cannot submit a decision that is not in draft status."""
    case = _make_case(db_session)
    svc = CaseDecisionService(db_session)

    decision = svc.create_decision(
        case_id=case.id,
        tenant_id=TENANT,
        disposition="no_action",
        rationale=None,
        created_by="user_a",
    )
    db_session.commit()

    # Submit once
    svc.submit_decision(decision.id, TENANT, "rationale text", "user_a")
    db_session.commit()

    # Try to submit again — should fail
    with pytest.raises(HTTPException) as exc_info:
        svc.submit_decision(decision.id, TENANT, "another rationale", "user_a")
    assert exc_info.value.status_code == 409


# ------------------------------------------------------------------
# approve_decision — 4-eyes
# ------------------------------------------------------------------


@pytest.mark.unit
def test_approve_decision_four_eyes(db_session):
    """Approval by a different user succeeds and auto-closes the case."""
    case = _make_case(db_session)
    svc = CaseDecisionService(db_session)

    decision = svc.create_decision(
        case_id=case.id,
        tenant_id=TENANT,
        disposition="no_action",
        rationale=None,
        created_by="creator@example.com",
    )
    db_session.commit()
    svc.submit_decision(decision.id, TENANT, "Detailed rationale here.", "creator@example.com")
    db_session.commit()

    approved = svc.approve_decision(
        decision_id=decision.id,
        tenant_id=TENANT,
        approver_id="approver@example.com",
        comment="Approved after review",
    )
    db_session.commit()

    assert approved.status == CaseDecisionStatus.approved.value
    assert approved.approver_id == "approver@example.com"
    assert approved.approved_at is not None

    # Case auto-closed
    db_session.refresh(case)
    assert case.status == "closed"
    assert case.outcome == "no_action"
    assert case.closed_at is not None

    # DecisionRecord created (immutable compliance record)
    dec_record = (
        db_session.query(DecisionRecord).filter(DecisionRecord.decision == "no_action").first()
    )
    assert dec_record is not None
    assert dec_record.evidence["approver"] == "approver@example.com"


@pytest.mark.unit
def test_approve_same_user_four_eyes_violation(db_session):
    """409 when the approver is the same as the creator."""
    case = _make_case(db_session)
    svc = CaseDecisionService(db_session)

    decision = svc.create_decision(
        case_id=case.id,
        tenant_id=TENANT,
        disposition="monitor",
        rationale=None,
        created_by="same_user@example.com",
    )
    db_session.commit()
    svc.submit_decision(decision.id, TENANT, "Rationale text", "same_user@example.com")
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        svc.approve_decision(
            decision_id=decision.id,
            tenant_id=TENANT,
            approver_id="same_user@example.com",
        )
    assert exc_info.value.status_code == 409
    assert "4-eyes" in exc_info.value.detail.lower()


@pytest.mark.unit
def test_approve_from_non_submitted_fails(db_session):
    """Cannot approve a decision that is still in draft."""
    case = _make_case(db_session)
    svc = CaseDecisionService(db_session)

    decision = svc.create_decision(
        case_id=case.id,
        tenant_id=TENANT,
        disposition="no_action",
        rationale=None,
        created_by="user_a",
    )
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        svc.approve_decision(decision.id, TENANT, "user_b")
    assert exc_info.value.status_code == 409


# ------------------------------------------------------------------
# reject_decision
# ------------------------------------------------------------------


@pytest.mark.unit
def test_reject_decision_keeps_case_open(db_session):
    """Rejection moves case back to in_progress (from decision_pending)."""
    case = _make_case(db_session)
    svc = CaseDecisionService(db_session)

    decision = svc.create_decision(
        case_id=case.id,
        tenant_id=TENANT,
        disposition="escalate",
        rationale=None,
        created_by="creator@example.com",
    )
    db_session.commit()
    svc.submit_decision(decision.id, TENANT, "Want to escalate", "creator@example.com")
    db_session.commit()

    # Case is now decision_pending
    db_session.refresh(case)
    assert case.status == "decision_pending"

    rejected = svc.reject_decision(
        decision_id=decision.id,
        tenant_id=TENANT,
        rejector_id="senior@example.com",
        rejection_reason="Need more evidence before escalation",
    )
    db_session.commit()

    assert rejected.status == CaseDecisionStatus.rejected.value
    assert rejected.rejection_reason == "Need more evidence before escalation"

    # Case back to in_progress
    db_session.refresh(case)
    assert case.status == "in_progress"

    # Audit event
    event = (
        db_session.query(EventRecord)
        .filter(
            EventRecord.event_type == "decision.rejected",
            EventRecord.entity_id == str(decision.id),
        )
        .first()
    )
    assert event is not None
    assert event.payload["rejector"] == "senior@example.com"


# ------------------------------------------------------------------
# Invalid transitions
# ------------------------------------------------------------------


@pytest.mark.unit
def test_invalid_transition_draft_to_approved(db_session):
    """Cannot go directly from draft → approved (must go through submitted)."""
    case = _make_case(db_session)
    svc = CaseDecisionService(db_session)

    decision = svc.create_decision(
        case_id=case.id,
        tenant_id=TENANT,
        disposition="no_action",
        rationale=None,
        created_by="user_a",
    )
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        svc.approve_decision(decision.id, TENANT, "user_b")
    assert exc_info.value.status_code == 409
    assert "invalid transition" in exc_info.value.detail.lower()


@pytest.mark.unit
def test_invalid_transition_draft_to_rejected(db_session):
    """Cannot go directly from draft → rejected."""
    case = _make_case(db_session)
    svc = CaseDecisionService(db_session)

    decision = svc.create_decision(
        case_id=case.id,
        tenant_id=TENANT,
        disposition="no_action",
        rationale=None,
        created_by="user_a",
    )
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        svc.reject_decision(decision.id, TENANT, "user_b", "reason")
    assert exc_info.value.status_code == 409


@pytest.mark.unit
def test_invalid_transition_approved_to_anything(db_session):
    """Cannot transition from an approved decision."""
    case = _make_case(db_session)
    svc = CaseDecisionService(db_session)

    decision = svc.create_decision(
        case_id=case.id,
        tenant_id=TENANT,
        disposition="no_action",
        rationale=None,
        created_by="creator@example.com",
    )
    db_session.commit()
    svc.submit_decision(decision.id, TENANT, "rationale", "creator@example.com")
    db_session.commit()
    svc.approve_decision(decision.id, TENANT, "approver@example.com")
    db_session.commit()

    # Try to submit again
    with pytest.raises(HTTPException) as exc_info:
        svc.submit_decision(decision.id, TENANT, "re-submit", "creator@example.com")
    assert exc_info.value.status_code == 409


# ------------------------------------------------------------------
# Decision not found
# ------------------------------------------------------------------


@pytest.mark.unit
def test_decision_not_found(db_session):
    """404 when decision doesn't exist."""
    svc = CaseDecisionService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        svc.submit_decision(999999, TENANT, "rationale", "user_a")
    assert exc_info.value.status_code == 404
