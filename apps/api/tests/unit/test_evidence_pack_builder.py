"""Unit tests for EvidencePackBuilder — snapshot assembly, canonicalization, hashing."""

import hashlib
import json

import pytest

from src.models.case_decision import CaseDecision, CaseDecisionStatus
from src.models.evidence_pack import EvidencePack
from src.models.finding_models import Finding, FindingStatus
from src.models.transaction_models import Case
from src.services.evidence_pack_builder import EvidencePackBuilder, _model_to_dict
from src.tenancy.context import set_current_tenant, clear_current_tenant
from tests.factories import CaseFactory, FindingFactory


TENANT = "default"


@pytest.fixture(autouse=True)
def _tenant_ctx():
    set_current_tenant(TENANT)
    yield
    clear_current_tenant()


def _make_case_with_finding(db_session) -> Case:
    """Create a case with one linked finding."""
    case = CaseFactory(
        sqlalchemy_session=db_session,
        tenant_id=TENANT,
        status="closed",
        outcome="no_action",
        case_type="investigation",
        subject_type="user",
        subject_id="user_test",
        priority="high",
        title="Evidence pack test case",
        related_alert_ids=[],
        related_transaction_ids=[],
    )
    finding = FindingFactory(
        sqlalchemy_session=db_session,
        tenant_id=TENANT,
        finding_type="TX_ALERT",
        severity="high",
        status=FindingStatus.escalated.value,
        title="Test finding",
        source_refs_json={"alert_id": "alert_001", "transaction_id": "txn_001"},
    )
    case.findings.append(finding)
    db_session.commit()
    return case


def _make_case_with_decision(db_session) -> Case:
    """Create a case with a finding and an approved decision."""
    case = _make_case_with_finding(db_session)

    decision = CaseDecision(
        tenant_id=TENANT,
        case_id=case.id,
        version=1,
        status=CaseDecisionStatus.approved.value,
        disposition="no_action",
        rationale="No suspicious activity found.",
        created_by="analyst@example.com",
        approver_id="senior@example.com",
    )
    db_session.add(decision)
    db_session.commit()
    return case


# ------------------------------------------------------------------
# Snapshot assembly
# ------------------------------------------------------------------


@pytest.mark.unit
def test_snapshot_includes_case_findings_decision(db_session):
    """build_snapshot returns case, findings, and decision data."""
    case = _make_case_with_decision(db_session)
    builder = EvidencePackBuilder(db_session)

    snapshot = builder.build_snapshot(case, TENANT)

    assert snapshot["schema_version"] == "v1"
    assert snapshot["tenant_id"] == TENANT
    assert "generated_at" in snapshot

    # Case
    assert snapshot["case"]["case_id"] == case.case_id
    assert snapshot["case"]["status"] == "closed"

    # Findings
    assert len(snapshot["findings"]) == 1
    assert snapshot["findings"][0]["finding_type"] == "TX_ALERT"

    # Decision (latest approved)
    assert snapshot["decision"] is not None
    assert snapshot["decision"]["disposition"] == "no_action"
    assert snapshot["decision"]["approver_id"] == "senior@example.com"

    # References extracted from findings
    assert "transactions" in snapshot["references"]
    assert "alerts" in snapshot["references"]

    # Integrity placeholder
    assert "integrity" in snapshot


@pytest.mark.unit
def test_snapshot_without_decision(db_session):
    """build_snapshot with no decision returns decision=None."""
    case = _make_case_with_finding(db_session)
    builder = EvidencePackBuilder(db_session)

    snapshot = builder.build_snapshot(case, TENANT)

    assert snapshot["decision"] is None
    assert len(snapshot["findings"]) == 1


@pytest.mark.unit
def test_snapshot_empty_case(db_session):
    """build_snapshot with no findings returns empty lists."""
    case = CaseFactory(
        sqlalchemy_session=db_session,
        tenant_id=TENANT,
        status="open",
        related_alert_ids=[],
        related_transaction_ids=[],
    )
    db_session.commit()

    builder = EvidencePackBuilder(db_session)
    snapshot = builder.build_snapshot(case, TENANT)

    assert snapshot["findings"] == []
    assert snapshot["decision"] is None
    assert snapshot["audit_timeline"] == []


# ------------------------------------------------------------------
# Canonicalization
# ------------------------------------------------------------------


@pytest.mark.unit
def test_canonicalize_deterministic():
    """Same input always produces same canonical JSON."""
    data = {"z": 1, "a": 2, "m": [3, 1, 2]}
    canonical1 = EvidencePackBuilder.canonicalize(data)
    canonical2 = EvidencePackBuilder.canonicalize(data)

    assert canonical1 == canonical2
    # Keys should be sorted
    parsed = json.loads(canonical1)
    assert list(parsed.keys()) == sorted(parsed.keys())


@pytest.mark.unit
def test_canonicalize_no_whitespace():
    """Canonical JSON has no extra whitespace."""
    data = {"key": "value", "nested": {"a": 1}}
    canonical = EvidencePackBuilder.canonicalize(data)
    assert " " not in canonical  # separators=(",", ":") means no spaces


@pytest.mark.unit
def test_canonicalize_handles_datetime():
    """Datetime objects are serialized via default=str."""
    from datetime import datetime, timezone

    data = {"time": datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)}
    canonical = EvidencePackBuilder.canonicalize(data)
    assert "2026-01-15" in canonical


# ------------------------------------------------------------------
# Hash computation
# ------------------------------------------------------------------


@pytest.mark.unit
def test_hash_matches_canonical():
    """compute_hash returns SHA-256 of the canonical JSON."""
    data = {"hello": "world", "count": 42}
    canonical = EvidencePackBuilder.canonicalize(data)
    computed = EvidencePackBuilder.compute_hash(canonical)

    expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    assert computed == expected
    assert len(computed) == 64


@pytest.mark.unit
def test_hash_changes_with_data():
    """Different data produces different hashes."""
    data1 = {"key": "value1"}
    data2 = {"key": "value2"}

    h1 = EvidencePackBuilder.compute_hash(EvidencePackBuilder.canonicalize(data1))
    h2 = EvidencePackBuilder.compute_hash(EvidencePackBuilder.canonicalize(data2))

    assert h1 != h2


# ------------------------------------------------------------------
# create_pack (full flow)
# ------------------------------------------------------------------


@pytest.mark.unit
def test_create_pack_json(db_session):
    """create_pack produces an EvidencePack with hash and snapshot."""
    case = _make_case_with_decision(db_session)
    builder = EvidencePackBuilder(db_session)

    pack = builder.create_pack(
        case_id=case.id,
        tenant_id=TENANT,
        created_by="auditor@example.com",
        pack_format="json",
    )
    db_session.commit()

    assert pack.id is not None
    assert pack.pack_id.startswith("EPACK-")
    assert pack.version == 1
    assert pack.format == "json"
    assert pack.schema_version == "v1"
    assert len(pack.integrity_hash) == 64

    # Snapshot should include the hash
    snapshot = pack.snapshot_json
    assert snapshot["integrity"]["content_hash"].startswith("sha256:")
    assert pack.integrity_hash in snapshot["integrity"]["content_hash"]

    # Storage ref should be None for JSON format
    assert pack.storage_ref is None

    # Verify hash integrity
    # Remove the hash to verify
    snapshot_copy = json.loads(json.dumps(snapshot, default=str))
    snapshot_copy["integrity"]["content_hash"] = ""
    canonical = EvidencePackBuilder.canonicalize(snapshot_copy)
    recomputed = EvidencePackBuilder.compute_hash(canonical)
    assert recomputed == pack.integrity_hash


@pytest.mark.unit
def test_version_auto_increment(db_session):
    """Second evidence pack for same case gets version=2."""
    case = _make_case_with_finding(db_session)
    builder = EvidencePackBuilder(db_session)

    pack1 = builder.create_pack(case.id, TENANT, "user_a")
    db_session.commit()

    pack2 = builder.create_pack(case.id, TENANT, "user_b")
    db_session.commit()

    assert pack1.version == 1
    assert pack2.version == 2
    assert pack1.pack_id != pack2.pack_id


@pytest.mark.unit
def test_create_pack_case_not_found(db_session):
    """ValueError if the case doesn't exist."""
    builder = EvidencePackBuilder(db_session)
    with pytest.raises(ValueError, match="Case not found"):
        builder.create_pack(999999, TENANT, "user_x")


# ------------------------------------------------------------------
# _model_to_dict helper
# ------------------------------------------------------------------


@pytest.mark.unit
def test_model_to_dict(db_session):
    """_model_to_dict converts a SQLAlchemy model to a plain dict."""
    finding = FindingFactory(
        sqlalchemy_session=db_session,
        tenant_id=TENANT,
        finding_type="TX_ALERT",
        severity="high",
        title="Dict test",
    )
    db_session.commit()

    result = _model_to_dict(finding)
    assert isinstance(result, dict)
    assert result["tenant_id"] == TENANT
    assert result["finding_type"] == "TX_ALERT"
    assert result["severity"] == "high"
    assert result["title"] == "Dict test"
    assert "id" in result


# ------------------------------------------------------------------
# Audit event on pack creation
# ------------------------------------------------------------------


@pytest.mark.unit
def test_create_pack_records_audit_event(db_session):
    """create_pack emits an evidence_pack.created audit event."""
    from src.audit.models import EventRecord

    case = _make_case_with_finding(db_session)
    builder = EvidencePackBuilder(db_session)

    pack = builder.create_pack(case.id, TENANT, "auditor@example.com")
    db_session.commit()

    event = (
        db_session.query(EventRecord)
        .filter(
            EventRecord.event_type == "evidence_pack.created",
            EventRecord.entity_id == pack.pack_id,
        )
        .first()
    )
    assert event is not None
    assert event.payload["case_id"] == case.case_id
    assert event.payload["format"] == "json"
    assert event.payload["integrity_hash"] == pack.integrity_hash
