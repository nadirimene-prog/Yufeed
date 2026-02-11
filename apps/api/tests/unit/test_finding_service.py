"""Unit tests for FindingService — idempotent upsert, close, and fingerprint normalization."""

import hashlib

import pytest

from src.models.finding_models import Finding, FindingStatus
from src.services.finding_service import FindingService
from src.audit.models import EventRecord
from src.tenancy.context import set_current_tenant, clear_current_tenant
from tests.factories import CaseFactory, FindingFactory


TENANT = "default"


@pytest.fixture(autouse=True)
def _tenant_ctx():
    set_current_tenant(TENANT)
    yield
    clear_current_tenant()


# ------------------------------------------------------------------
# create_or_update_finding — new
# ------------------------------------------------------------------


@pytest.mark.unit
def test_create_new_finding(db_session):
    """Creating a brand-new finding returns (finding, True) and persists it."""
    svc = FindingService(db_session)
    finding, is_new = svc.create_or_update_finding(
        tenant_id=TENANT,
        finding_type="TX_ALERT",
        fingerprint="default:TX_ALERT:txn_001:rule_001",
        severity="high",
        title="High-value transaction",
        summary="Transaction of 50k USD",
        source_refs={"alert_id": "alert_001", "transaction_id": "txn_001"},
        explainability={"evidence": "amount > threshold"},
    )

    assert is_new is True
    assert finding.id is not None
    assert finding.tenant_id == TENANT
    assert finding.finding_type == "TX_ALERT"
    assert finding.severity == "high"
    assert finding.status == FindingStatus.new.value
    assert finding.title == "High-value transaction"
    assert finding.source_refs_json["alert_id"] == "alert_001"
    assert finding.fingerprint == "default:TX_ALERT:txn_001:rule_001"

    # Flush to persist event records before querying
    db_session.flush()

    # Verify audit event recorded
    events = (
        db_session.query(EventRecord)
        .filter(
            EventRecord.event_type == "finding.created",
            EventRecord.entity_id == str(finding.id),
        )
        .all()
    )
    assert len(events) == 1
    assert events[0].payload["finding_type"] == "TX_ALERT"


# ------------------------------------------------------------------
# create_or_update_finding — upsert existing (merge refs)
# ------------------------------------------------------------------


@pytest.mark.unit
def test_upsert_existing_merges_refs(db_session):
    """Upserting an existing finding merges source_refs without overwriting."""
    svc = FindingService(db_session)
    fp = "default:TX_ALERT:txn_002:rule_002"

    # First creation
    finding, is_new = svc.create_or_update_finding(
        tenant_id=TENANT,
        finding_type="TX_ALERT",
        fingerprint=fp,
        severity="medium",
        title="First finding",
        source_refs={"alert_id": "alert_002"},
        explainability={"initial": True},
    )
    db_session.commit()
    assert is_new is True
    original_id = finding.id

    # Second call with same fingerprint — should update, not create
    finding2, is_new2 = svc.create_or_update_finding(
        tenant_id=TENANT,
        finding_type="TX_ALERT",
        fingerprint=fp,
        severity="high",
        title="Updated title",
        source_refs={"transaction_id": "txn_002"},
        explainability={"updated": True},
    )
    db_session.commit()

    assert is_new2 is False
    assert finding2.id == original_id
    # source_refs should be merged
    assert finding2.source_refs_json["alert_id"] == "alert_002"
    assert finding2.source_refs_json["transaction_id"] == "txn_002"
    # explainability is replaced
    assert finding2.explainability_json == {"updated": True}
    # severity and title updated
    assert finding2.severity == "high"
    assert finding2.title == "Updated title"

    # Only one Finding in DB for this fingerprint
    count = (
        db_session.query(Finding)
        .filter(Finding.tenant_id == TENANT, Finding.fingerprint == fp)
        .count()
    )
    assert count == 1

    # Verify audit events: 1 created + 1 updated
    events = (
        db_session.query(EventRecord)
        .filter(EventRecord.entity_id == str(original_id))
        .order_by(EventRecord.created_at)
        .all()
    )
    types = [e.event_type for e in events]
    assert "finding.created" in types
    assert "finding.updated" in types


# ------------------------------------------------------------------
# create_or_update_finding — reopen closed finding
# ------------------------------------------------------------------


@pytest.mark.unit
def test_upsert_reopens_closed_finding(db_session):
    """A closed finding is reopened (status → new) when updated via upsert."""
    svc = FindingService(db_session)
    fp = "default:TX_ALERT:txn_003:rule_003"

    # Create and close
    finding, _ = svc.create_or_update_finding(
        tenant_id=TENANT,
        finding_type="TX_ALERT",
        fingerprint=fp,
        severity="low",
        title="Will be closed",
    )
    db_session.flush()

    svc.close_finding(finding, "false_positive", "not a real threat", actor_id="user_a")
    db_session.commit()
    assert finding.status == FindingStatus.closed.value
    assert finding.closed_reason == "false_positive"

    # Upsert with same fingerprint — should reopen
    reopened, is_new = svc.create_or_update_finding(
        tenant_id=TENANT,
        finding_type="TX_ALERT",
        fingerprint=fp,
        severity="high",
        title="Reopened",
        source_refs={"new_alert": "alert_new"},
    )
    db_session.commit()

    assert is_new is False
    assert reopened.id == finding.id
    assert reopened.status == FindingStatus.new.value
    assert reopened.closed_reason is None
    assert reopened.closed_comment is None


# ------------------------------------------------------------------
# close_finding
# ------------------------------------------------------------------


@pytest.mark.unit
def test_close_finding(db_session):
    """close_finding sets status, reason, comment and emits audit event."""
    svc = FindingService(db_session)
    finding, _ = svc.create_or_update_finding(
        tenant_id=TENANT,
        finding_type="SANCTIONS_HIT",
        fingerprint="default:SANC:subject_1:name_1:ofac",
        severity="critical",
        title="Sanctions match",
    )
    db_session.flush()

    closed = svc.close_finding(
        finding,
        closed_reason="resolved",
        closed_comment="Confirmed false match after manual review",
        actor_id="analyst@example.com",
    )
    db_session.commit()

    assert closed.status == FindingStatus.closed.value
    assert closed.closed_reason == "resolved"
    assert closed.closed_comment == "Confirmed false match after manual review"

    # Audit event
    event = (
        db_session.query(EventRecord)
        .filter(
            EventRecord.event_type == "finding.closed",
            EventRecord.entity_id == str(finding.id),
        )
        .first()
    )
    assert event is not None
    assert event.payload["closed_reason"] == "resolved"
    assert event.payload["actor"] == "analyst@example.com"


# ------------------------------------------------------------------
# Fingerprint normalization
# ------------------------------------------------------------------


@pytest.mark.unit
def test_fingerprint_normalization_short_input():
    """Short fingerprints (< 8 chars) are hashed for stability."""
    result = FindingService._normalize_fingerprint("tenant1", "abc")
    # Should be a SHA-256 hex prefix (64 chars, truncated to 128 max)
    expected = hashlib.sha256("tenant1:abc".encode("utf-8")).hexdigest()[:128]
    assert result == expected
    assert len(result) == 64  # SHA-256 hex = 64 chars


@pytest.mark.unit
def test_fingerprint_normalization_long_input():
    """Long fingerprints (> 128 chars) are truncated."""
    long_fp = "x" * 200
    result = FindingService._normalize_fingerprint("tenant1", long_fp)
    assert len(result) == 128
    assert result == long_fp[:128]


@pytest.mark.unit
def test_fingerprint_normalization_normal_input():
    """Normal-length fingerprints are returned as-is."""
    fp = "default:TX_ALERT:txn_123:rule_456"
    result = FindingService._normalize_fingerprint("tenant1", fp)
    assert result == fp


# ------------------------------------------------------------------
# Tenant isolation
# ------------------------------------------------------------------


@pytest.mark.unit
def test_findings_isolated_by_tenant(db_session):
    """Findings with same fingerprint but different tenants are distinct."""
    svc = FindingService(db_session)
    fp = "shared:TX_ALERT:txn_cross:rule_cross"

    f1, new1 = svc.create_or_update_finding(
        tenant_id="tenant_a",
        finding_type="TX_ALERT",
        fingerprint=fp,
        severity="high",
        title="Tenant A finding",
    )
    db_session.flush()

    f2, new2 = svc.create_or_update_finding(
        tenant_id="tenant_b",
        finding_type="TX_ALERT",
        fingerprint=fp,
        severity="low",
        title="Tenant B finding",
    )
    db_session.commit()

    assert new1 is True
    assert new2 is True
    assert f1.id != f2.id
    assert f1.tenant_id == "tenant_a"
    assert f2.tenant_id == "tenant_b"


# ------------------------------------------------------------------
# Severity normalization
# ------------------------------------------------------------------


@pytest.mark.unit
def test_severity_normalized_to_lowercase(db_session):
    """Severity is lowercased and stripped."""
    svc = FindingService(db_session)
    finding, _ = svc.create_or_update_finding(
        tenant_id=TENANT,
        finding_type="OTHER",
        fingerprint="default:OTHER:test_sev_normalize",
        severity="  HIGH  ",
        title="Severity test",
    )
    db_session.commit()
    assert finding.severity == "high"
