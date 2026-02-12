"""Integration tests for enhanced Findings API — filters, close, escalate, audit."""

import pytest
from datetime import datetime, timezone, timedelta

from src.api import findings as findings_api
from src.models.finding_models import Finding, FindingStatus
from src.models.transaction_models import Case
from src.audit.models import EventRecord
from src.services.finding_service import FindingService
from src.schemas.finding_schemas import (
    FindingCreate,
    FindingUpdate,
    FindingCloseRequest,
    EscalateToCaseRequest,
)
from src.tenancy.context import set_current_tenant, clear_current_tenant
from tests.factories import FindingFactory


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


# ------------------------------------------------------------------
# CREATE (idempotent via FindingService)
# ------------------------------------------------------------------


@pytest.mark.unit
def test_create_finding_via_api(db_session):
    """POST /findings creates a finding via FindingService."""
    payload = FindingCreate(
        finding_type="TX_ALERT",
        fingerprint="default:TX_ALERT:txn_api_001:rule_001",
        severity="high",
        title="API test finding",
        summary="Created via API layer",
        source_refs={"alert_id": "a001"},
    )
    result = findings_api.create_finding(payload, db=db_session, current_user=_FakeUser())

    assert result.id is not None
    assert result.finding_type == "TX_ALERT"
    assert result.severity == "high"
    assert result.status == FindingStatus.new.value


@pytest.mark.unit
def test_create_finding_idempotent(db_session):
    """Same fingerprint returns the existing finding (upsert)."""
    fp = "default:TX_ALERT:txn_api_idem:rule_001"
    payload = FindingCreate(
        finding_type="TX_ALERT",
        fingerprint=fp,
        severity="medium",
        title="First",
    )
    r1 = findings_api.create_finding(payload, db=db_session, current_user=_FakeUser())

    payload2 = FindingCreate(
        finding_type="TX_ALERT",
        fingerprint=fp,
        severity="high",
        title="Updated title",
    )
    r2 = findings_api.create_finding(payload2, db=db_session, current_user=_FakeUser())

    assert r1.id == r2.id  # same record
    assert r2.severity == "high"
    assert r2.title == "Updated title"


# ------------------------------------------------------------------
# LIST with filters
# ------------------------------------------------------------------


def _list_findings(db_session, **overrides):
    """Call list_findings with all Query defaults explicitly set."""
    user = overrides.pop("current_user", _FakeUser())
    defaults = dict(
        status=None,
        finding_type=None,
        severity=None,
        assigned_to=None,
        from_date=None,
        to_date=None,
        q=None,
        sort="created_at_desc",
        limit=50,
        offset=0,
    )
    defaults.update(overrides)
    return findings_api.list_findings(db=db_session, current_user=user, **defaults)


@pytest.mark.unit
def test_list_findings_severity_filter(db_session):
    """Filter by severity (comma-separated)."""
    svc = FindingService(db_session)
    svc.create_or_update_finding(TENANT, "TX_ALERT", f"{TENANT}:TX:s1", severity="high", title="H1")
    svc.create_or_update_finding(TENANT, "TX_ALERT", f"{TENANT}:TX:s2", severity="low", title="L1")
    svc.create_or_update_finding(
        TENANT, "TX_ALERT", f"{TENANT}:TX:s3", severity="critical", title="C1"
    )
    db_session.commit()

    results = _list_findings(db_session, severity="high,critical")
    severities = {r.severity for r in results}
    assert "high" in severities
    assert "critical" in severities
    assert "low" not in severities


@pytest.mark.unit
def test_list_findings_text_search(db_session):
    """Free-text search (q) matches title and summary via ILIKE."""
    svc = FindingService(db_session)
    svc.create_or_update_finding(
        TENANT,
        "TX_ALERT",
        f"{TENANT}:TX:q1",
        severity="medium",
        title="Suspicious wire transfer",
        summary="Over 50k",
    )
    svc.create_or_update_finding(
        TENANT,
        "TX_ALERT",
        f"{TENANT}:TX:q2",
        severity="medium",
        title="Normal trade",
        summary="Nothing notable",
    )
    db_session.commit()

    results = _list_findings(db_session, q="wire")
    assert len(results) >= 1
    assert any("wire" in (r.title or "").lower() for r in results)


@pytest.mark.unit
def test_list_findings_date_range(db_session):
    """Filter by from_date and to_date."""
    now = datetime.now(timezone.utc)
    svc = FindingService(db_session)
    f, _ = svc.create_or_update_finding(
        TENANT,
        "TX_ALERT",
        f"{TENANT}:TX:dt1",
        severity="medium",
        title="Date range test",
    )
    db_session.commit()

    # Should find it with wide range
    results = _list_findings(
        db_session,
        from_date=now - timedelta(hours=1),
        to_date=now + timedelta(hours=1),
    )
    assert any(r.id == f.id for r in results)

    # Should NOT find it with past range
    results = _list_findings(
        db_session,
        from_date=now - timedelta(days=30),
        to_date=now - timedelta(days=29),
    )
    assert not any(r.id == f.id for r in results)


@pytest.mark.unit
def test_list_findings_sort_created_at_asc(db_session):
    """Sort by created_at ascending."""
    svc = FindingService(db_session)
    svc.create_or_update_finding(TENANT, "TX_ALERT", f"{TENANT}:TX:sort1", title="First")
    svc.create_or_update_finding(TENANT, "TX_ALERT", f"{TENANT}:TX:sort2", title="Second")
    db_session.commit()

    results = _list_findings(db_session, sort="created_at_asc")
    assert len(results) >= 2
    # First result should have earlier or equal timestamp
    if len(results) >= 2:
        assert results[0].created_at <= results[1].created_at


# ------------------------------------------------------------------
# CLOSE
# ------------------------------------------------------------------


@pytest.mark.unit
def test_close_finding_via_api(db_session):
    """POST /findings/{id}/close sets closed status and reason."""
    svc = FindingService(db_session)
    finding, _ = svc.create_or_update_finding(
        TENANT,
        "TX_ALERT",
        f"{TENANT}:TX:close1",
        severity="low",
        title="Will close",
    )
    db_session.commit()

    payload = FindingCloseRequest(closed_reason="false_positive", closed_comment="Manual review OK")
    result = findings_api.close_finding(
        finding.id, payload, db=db_session, current_user=_FakeUser()
    )

    assert result.status == FindingStatus.closed.value
    assert result.closed_reason == "false_positive"
    assert result.closed_comment == "Manual review OK"


@pytest.mark.unit
def test_close_already_closed_409(db_session):
    """Closing an already-closed finding returns 409."""
    svc = FindingService(db_session)
    finding, _ = svc.create_or_update_finding(
        TENANT,
        "TX_ALERT",
        f"{TENANT}:TX:close2",
        severity="low",
        title="Already closed",
    )
    svc.close_finding(finding, "resolved", None, "user_a")
    db_session.commit()

    from fastapi import HTTPException

    payload = FindingCloseRequest(closed_reason="duplicate")
    with pytest.raises(HTTPException) as exc_info:
        findings_api.close_finding(finding.id, payload, db=db_session, current_user=_FakeUser())
    assert exc_info.value.status_code == 409


# ------------------------------------------------------------------
# ESCALATE to Case
# ------------------------------------------------------------------


@pytest.mark.unit
def test_escalate_finding_creates_case(db_session):
    """POST /findings/{id}/escalate creates a new case and links the finding."""
    svc = FindingService(db_session)
    finding, _ = svc.create_or_update_finding(
        TENANT,
        "TX_ALERT",
        f"{TENANT}:TX:esc1",
        severity="high",
        title="Escalate me",
    )
    db_session.commit()

    payload = EscalateToCaseRequest(title="New case from finding", priority="high")
    result = findings_api.escalate_finding_to_case(
        finding.id, payload, db=db_session, current_user=_FakeUser()
    )

    assert result.case_id.startswith("CAS-")
    assert result.status == "open"

    # Finding should be escalated
    db_session.refresh(finding)
    assert finding.status == FindingStatus.escalated.value

    # Audit events
    db_session.flush()
    events = (
        db_session.query(EventRecord)
        .filter(
            EventRecord.event_type == "finding.escalated",
            EventRecord.entity_id == str(finding.id),
        )
        .all()
    )
    assert len(events) >= 1


@pytest.mark.unit
def test_escalate_idempotent(db_session):
    """Second escalation returns the existing case (idempotent)."""
    svc = FindingService(db_session)
    finding, _ = svc.create_or_update_finding(
        TENANT,
        "TX_ALERT",
        f"{TENANT}:TX:esc_idem",
        severity="high",
        title="Escalate once",
    )
    db_session.commit()

    payload = EscalateToCaseRequest(title="Case A")
    r1 = findings_api.escalate_finding_to_case(
        finding.id, payload, db=db_session, current_user=_FakeUser()
    )
    r2 = findings_api.escalate_finding_to_case(
        finding.id, EscalateToCaseRequest(title="Case B"), db=db_session, current_user=_FakeUser()
    )

    assert r1.case_id == r2.case_id  # same case returned


# ------------------------------------------------------------------
# UPDATE with audit trail
# ------------------------------------------------------------------


@pytest.mark.unit
def test_update_finding_records_audit(db_session):
    """PATCH /findings/{id} records an audit event."""
    svc = FindingService(db_session)
    finding, _ = svc.create_or_update_finding(
        TENANT,
        "TX_ALERT",
        f"{TENANT}:TX:upd1",
        severity="low",
        title="Will update",
    )
    db_session.commit()

    payload = FindingUpdate(severity="critical", assigned_to="senior@example.com")
    result = findings_api.update_finding(
        finding.id, payload, db=db_session, current_user=_FakeUser()
    )

    assert result.severity == "critical"
    assert result.assigned_to == "senior@example.com"

    db_session.flush()
    events = (
        db_session.query(EventRecord)
        .filter(
            EventRecord.event_type == "finding.updated",
            EventRecord.entity_id == str(finding.id),
        )
        .all()
    )
    # At least 1 from service create + 1 from API update
    assert len(events) >= 1
