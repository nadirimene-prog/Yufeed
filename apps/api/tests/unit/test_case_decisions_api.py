"""Integration tests for Case Decisions API — full governance workflow.

Tests the decision state machine through the API layer:
create draft → submit → approve (4-eyes) / reject.
"""

import pytest
from fastapi import HTTPException

from src.api import case_decisions as decisions_api
from src.models.case_decision import CaseDecision, CaseDecisionStatus
from src.models.transaction_models import Case
from src.audit.models import EventRecord, DecisionRecord
from src.schemas.case_decision_schemas import (
    CaseDecisionCreate,
    CaseDecisionSubmit,
    CaseDecisionApprove,
    CaseDecisionReject,
)
from src.tenancy.context import set_current_tenant, clear_current_tenant
from tests.factories import CaseFactory


TENANT = "default"


class _FakeUser:
    """Minimal mock for CurrentUser dependency."""

    def __init__(
        self,
        user_id="test-analyst",
        email="analyst@example.com",
        role="compliance",
        tenant_id=TENANT,
    ):
        self.user_id = user_id
        self.email = email
        self.role = role
        self.tenant_id = tenant_id
        self.is_superuser = False


@pytest.fixture(autouse=True)
def _tenant_ctx():
    set_current_tenant(TENANT)
    yield
    clear_current_tenant()


@pytest.fixture
def case(db_session) -> Case:
    """Create a test case and return it."""
    c = CaseFactory(
        sqlalchemy_session=db_session,
        tenant_id=TENANT,
        status="open",
        case_type="investigation",
        subject_type="user",
        subject_id="user_test",
        priority="medium",
        title="Decisions test case",
    )
    return c


# ------------------------------------------------------------------
# CREATE draft
# ------------------------------------------------------------------


@pytest.mark.unit
def test_create_decision_api(db_session, case):
    """POST creates a draft decision and returns response."""
    payload = CaseDecisionCreate(disposition="no_action", rationale="Initial draft")
    creator = _FakeUser(user_id="creator@example.com")

    result = decisions_api.create_decision(
        case_id=case.case_id,
        payload=payload,
        db=db_session,
        current_user=creator,
    )

    assert result.id is not None
    assert result.version == 1
    assert result.status == CaseDecisionStatus.draft.value
    assert result.disposition == "no_action"
    assert result.created_by == "creator@example.com"


# ------------------------------------------------------------------
# LIST
# ------------------------------------------------------------------


@pytest.mark.unit
def test_list_decisions_api(db_session, case):
    """GET lists decisions ordered by version desc."""
    creator = _FakeUser(user_id="creator@example.com")

    decisions_api.create_decision(
        case.case_id,
        CaseDecisionCreate(disposition="monitor"),
        db_session,
        creator,
    )
    decisions_api.create_decision(
        case.case_id,
        CaseDecisionCreate(disposition="no_action"),
        db_session,
        creator,
    )

    results = decisions_api.list_decisions(
        case_id=case.case_id,
        db=db_session,
        current_user=creator,
    )

    assert len(results) == 2
    assert results[0].version > results[1].version  # desc order


# ------------------------------------------------------------------
# GET single
# ------------------------------------------------------------------


@pytest.mark.unit
def test_get_decision_api(db_session, case):
    """GET /{decision_id} returns a single decision."""
    creator = _FakeUser(user_id="creator@example.com")

    decision = decisions_api.create_decision(
        case.case_id,
        CaseDecisionCreate(disposition="remediate"),
        db_session,
        creator,
    )

    result = decisions_api.get_decision(
        case_id=case.case_id,
        decision_id=decision.id,
        db=db_session,
        current_user=creator,
    )
    assert result.id == decision.id
    assert result.disposition == "remediate"


@pytest.mark.unit
def test_get_decision_not_found(db_session, case):
    """GET /{decision_id} returns 404 for non-existent decision."""
    with pytest.raises(HTTPException) as exc_info:
        decisions_api.get_decision(
            case_id=case.case_id,
            decision_id=999999,
            db=db_session,
            current_user=_FakeUser(),
        )
    assert exc_info.value.status_code == 404


# ------------------------------------------------------------------
# Full workflow: create → submit → approve
# ------------------------------------------------------------------


@pytest.mark.unit
def test_full_workflow_approve(db_session, case):
    """Complete workflow: draft → submitted → approved, case auto-closed."""
    creator = _FakeUser(user_id="creator@example.com")
    approver = _FakeUser(user_id="approver@example.com")

    # 1. Create draft
    decision = decisions_api.create_decision(
        case.case_id,
        CaseDecisionCreate(disposition="sar_required"),
        db_session,
        creator,
    )
    assert decision.status == CaseDecisionStatus.draft.value

    # 2. Submit
    submitted = decisions_api.submit_decision(
        case_id=case.case_id,
        decision_id=decision.id,
        payload=CaseDecisionSubmit(rationale="After thorough analysis, SAR is needed."),
        db=db_session,
        current_user=creator,
    )
    assert submitted.status == CaseDecisionStatus.submitted.value
    assert submitted.submitted_at is not None

    # Case should be decision_pending
    db_session.refresh(case)
    assert case.status == "decision_pending"

    # 3. Approve (different user — 4-eyes)
    approved = decisions_api.approve_decision(
        case_id=case.case_id,
        decision_id=decision.id,
        payload=CaseDecisionApprove(comment="Approved after review"),
        db=db_session,
        current_user=approver,
    )
    assert approved.status == CaseDecisionStatus.approved.value
    assert approved.approver_id == "approver@example.com"
    assert approved.approved_at is not None

    # Case auto-closed
    db_session.refresh(case)
    assert case.status == "closed"
    assert case.outcome == "sar_required"


# ------------------------------------------------------------------
# Full workflow: create → submit → reject
# ------------------------------------------------------------------


@pytest.mark.unit
def test_full_workflow_reject(db_session, case):
    """Complete workflow: draft → submitted → rejected, case back to in_progress."""
    creator = _FakeUser(user_id="creator@example.com")
    reviewer = _FakeUser(user_id="reviewer@example.com")

    decision = decisions_api.create_decision(
        case.case_id,
        CaseDecisionCreate(disposition="escalate"),
        db_session,
        creator,
    )
    decisions_api.submit_decision(
        case.case_id,
        decision.id,
        CaseDecisionSubmit(rationale="Needs escalation to senior team."),
        db_session,
        creator,
    )

    rejected = decisions_api.reject_decision(
        case_id=case.case_id,
        decision_id=decision.id,
        payload=CaseDecisionReject(rejection_reason="More evidence needed before escalating."),
        db=db_session,
        current_user=reviewer,
    )
    assert rejected.status == CaseDecisionStatus.rejected.value
    assert rejected.rejection_reason == "More evidence needed before escalating."

    db_session.refresh(case)
    assert case.status == "in_progress"


# ------------------------------------------------------------------
# 4-eyes violation
# ------------------------------------------------------------------


@pytest.mark.unit
def test_approve_same_user_blocked(db_session, case):
    """4-eyes: creator cannot approve their own decision."""
    same_user = _FakeUser(user_id="same@example.com")

    decision = decisions_api.create_decision(
        case.case_id,
        CaseDecisionCreate(disposition="no_action"),
        db_session,
        same_user,
    )
    decisions_api.submit_decision(
        case.case_id,
        decision.id,
        CaseDecisionSubmit(rationale="Self-approve test rationale."),
        db_session,
        same_user,
    )

    with pytest.raises(HTTPException) as exc_info:
        decisions_api.approve_decision(
            case.case_id,
            decision.id,
            CaseDecisionApprove(),
            db_session,
            same_user,  # same user as creator
        )
    assert exc_info.value.status_code == 409
    assert "4-eyes" in exc_info.value.detail.lower()


# ------------------------------------------------------------------
# Invalid transition
# ------------------------------------------------------------------


@pytest.mark.unit
def test_approve_draft_blocked(db_session, case):
    """Cannot approve a draft (must submit first)."""
    creator = _FakeUser(user_id="creator@example.com")
    approver = _FakeUser(user_id="approver@example.com")

    decision = decisions_api.create_decision(
        case.case_id,
        CaseDecisionCreate(disposition="no_action"),
        db_session,
        creator,
    )

    with pytest.raises(HTTPException) as exc_info:
        decisions_api.approve_decision(
            case.case_id,
            decision.id,
            CaseDecisionApprove(),
            db_session,
            approver,
        )
    assert exc_info.value.status_code == 409


# ------------------------------------------------------------------
# Case not found
# ------------------------------------------------------------------


@pytest.mark.unit
def test_create_decision_case_not_found(db_session):
    """404 when case does not exist."""
    with pytest.raises(HTTPException) as exc_info:
        decisions_api.create_decision(
            case_id="CAS-NONEXISTENT-000",
            payload=CaseDecisionCreate(disposition="no_action"),
            db=db_session,
            current_user=_FakeUser(),
        )
    assert exc_info.value.status_code == 404


# ------------------------------------------------------------------
# Audit trail
# ------------------------------------------------------------------


@pytest.mark.unit
def test_decision_workflow_audit_events(db_session, case):
    """Full workflow produces expected audit events."""
    creator = _FakeUser(user_id="creator@example.com")
    approver = _FakeUser(user_id="approver@example.com")

    decision = decisions_api.create_decision(
        case.case_id,
        CaseDecisionCreate(disposition="false_positive"),
        db_session,
        creator,
    )
    decisions_api.submit_decision(
        case.case_id,
        decision.id,
        CaseDecisionSubmit(rationale="Detailed rationale text here."),
        db_session,
        creator,
    )
    decisions_api.approve_decision(
        case.case_id,
        decision.id,
        CaseDecisionApprove(),
        db_session,
        approver,
    )
    db_session.flush()

    events = (
        db_session.query(EventRecord)
        .filter(EventRecord.entity_id == str(decision.id))
        .order_by(EventRecord.created_at)
        .all()
    )
    types = [e.event_type for e in events]
    assert "decision.created" in types
    assert "decision.submitted" in types
    assert "decision.approved" in types

    # DecisionRecord also created
    dec_record = (
        db_session.query(DecisionRecord).filter(DecisionRecord.decision == "false_positive").first()
    )
    assert dec_record is not None
