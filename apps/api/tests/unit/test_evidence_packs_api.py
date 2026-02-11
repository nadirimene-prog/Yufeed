"""Integration tests for Evidence Packs API — create, list, get, download."""

import json

import pytest
from fastapi import HTTPException

from src.api import evidence_packs as ep_api
from src.models.case_decision import CaseDecision, CaseDecisionStatus
from src.models.evidence_pack import EvidencePack
from src.models.finding_models import Finding, FindingStatus
from src.audit.models import EventRecord
from src.schemas.evidence_pack_schemas import EvidencePackCreateRequest
from src.services.evidence_pack_builder import EvidencePackBuilder
from src.tenancy.context import set_current_tenant, clear_current_tenant
from tests.factories import CaseFactory, FindingFactory


TENANT = "default"


class _FakeUser:
    """Minimal mock for CurrentUser dependency."""

    def __init__(
        self,
        user_id="test-auditor",
        email="auditor@example.com",
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
def case_with_finding(db_session):
    """Create a case with a linked finding and approved decision."""
    case = CaseFactory(
        sqlalchemy_session=db_session,
        tenant_id=TENANT,
        status="closed",
        outcome="no_action",
        case_type="investigation",
        subject_type="user",
        subject_id="user_ep",
        priority="high",
        title="Evidence pack API test case",
        related_alert_ids=[],
        related_transaction_ids=[],
    )
    finding = FindingFactory(
        sqlalchemy_session=db_session,
        tenant_id=TENANT,
        finding_type="TX_ALERT",
        severity="high",
        status=FindingStatus.escalated.value,
        title="EP test finding",
        source_refs_json={"alert_id": "a001", "transaction_id": "t001"},
    )
    case.findings.append(finding)

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
# CREATE
# ------------------------------------------------------------------


@pytest.mark.unit
def test_create_evidence_pack_json(db_session, case_with_finding):
    """POST creates a JSON evidence pack with snapshot and hash."""
    case = case_with_finding
    payload = EvidencePackCreateRequest(format="json")

    result = ep_api.create_evidence_pack(
        case_id=case.case_id,
        payload=payload,
        db=db_session,
        current_user=_FakeUser(),
    )

    assert result.pack_id.startswith("EPACK-")
    assert result.version == 1
    assert result.format == "json"
    assert result.schema_version == "v1"
    assert len(result.integrity_hash) == 64


@pytest.mark.unit
def test_create_evidence_pack_case_not_found(db_session):
    """POST returns 404 for non-existent case."""
    with pytest.raises(HTTPException) as exc_info:
        ep_api.create_evidence_pack(
            case_id="CAS-NONEXISTENT-999",
            payload=EvidencePackCreateRequest(format="json"),
            db=db_session,
            current_user=_FakeUser(),
        )
    assert exc_info.value.status_code == 404


# ------------------------------------------------------------------
# LIST
# ------------------------------------------------------------------


@pytest.mark.unit
def test_list_evidence_packs(db_session, case_with_finding):
    """GET lists packs for a case, ordered by version desc."""
    case = case_with_finding
    user = _FakeUser()

    ep_api.create_evidence_pack(
        case.case_id,
        EvidencePackCreateRequest(format="json"),
        db_session,
        user,
    )
    ep_api.create_evidence_pack(
        case.case_id,
        EvidencePackCreateRequest(format="json"),
        db_session,
        user,
    )

    results = ep_api.list_evidence_packs(
        case_id=case.case_id,
        db=db_session,
        current_user=user,
    )

    assert len(results) == 2
    assert results[0].version > results[1].version  # desc


@pytest.mark.unit
def test_list_evidence_packs_empty(db_session):
    """GET returns empty list for case with no packs."""
    case = CaseFactory(
        sqlalchemy_session=db_session,
        tenant_id=TENANT,
        status="open",
        related_alert_ids=[],
        related_transaction_ids=[],
    )
    db_session.commit()

    results = ep_api.list_evidence_packs(
        case_id=case.case_id,
        db=db_session,
        current_user=_FakeUser(),
    )
    assert results == []


# ------------------------------------------------------------------
# GET (detail with snapshot)
# ------------------------------------------------------------------


@pytest.mark.unit
def test_get_evidence_pack_detail(db_session, case_with_finding):
    """GET /{pack_id} returns full snapshot."""
    case = case_with_finding
    user = _FakeUser()

    created = ep_api.create_evidence_pack(
        case.case_id,
        EvidencePackCreateRequest(format="json"),
        db_session,
        user,
    )

    result = ep_api.get_evidence_pack(
        case_id=case.case_id,
        pack_id=created.pack_id,
        db=db_session,
        current_user=user,
    )

    assert result.pack_id == created.pack_id
    assert result.snapshot_json is not None
    assert result.snapshot_json["schema_version"] == "v1"
    assert result.snapshot_json["case"]["case_id"] == case.case_id
    assert len(result.snapshot_json["findings"]) >= 1
    assert result.snapshot_json["decision"] is not None


@pytest.mark.unit
def test_get_evidence_pack_not_found(db_session, case_with_finding):
    """GET /{pack_id} returns 404 for non-existent pack."""
    with pytest.raises(HTTPException) as exc_info:
        ep_api.get_evidence_pack(
            case_id=case_with_finding.case_id,
            pack_id="EPACK-NONEXISTENT",
            db=db_session,
            current_user=_FakeUser(),
        )
    assert exc_info.value.status_code == 404


# ------------------------------------------------------------------
# DOWNLOAD
# ------------------------------------------------------------------


@pytest.mark.unit
def test_download_json_evidence_pack(db_session, case_with_finding):
    """GET /{pack_id}/download returns canonical JSON with integrity header."""
    case = case_with_finding
    user = _FakeUser()

    created = ep_api.create_evidence_pack(
        case.case_id,
        EvidencePackCreateRequest(format="json"),
        db_session,
        user,
    )

    response = ep_api.download_evidence_pack(
        case_id=case.case_id,
        pack_id=created.pack_id,
        db=db_session,
        current_user=user,
    )

    # Should be a Response with JSON content
    assert response.media_type == "application/json"
    assert "X-Integrity-Hash" in response.headers
    assert response.headers["X-Integrity-Hash"] == created.integrity_hash

    # Content should be valid JSON
    content = json.loads(response.body)
    assert "schema_version" in content
    assert "integrity" in content


@pytest.mark.unit
def test_download_pack_not_found(db_session, case_with_finding):
    """GET /{pack_id}/download returns 404 for non-existent pack."""
    with pytest.raises(HTTPException) as exc_info:
        ep_api.download_evidence_pack(
            case_id=case_with_finding.case_id,
            pack_id="EPACK-NONEXISTENT",
            db=db_session,
            current_user=_FakeUser(),
        )
    assert exc_info.value.status_code == 404


# ------------------------------------------------------------------
# Version auto-increment
# ------------------------------------------------------------------


@pytest.mark.unit
def test_pack_version_increments(db_session, case_with_finding):
    """Multiple packs for same case get incrementing versions."""
    case = case_with_finding
    user = _FakeUser()

    p1 = ep_api.create_evidence_pack(
        case.case_id,
        EvidencePackCreateRequest(format="json"),
        db_session,
        user,
    )
    p2 = ep_api.create_evidence_pack(
        case.case_id,
        EvidencePackCreateRequest(format="json"),
        db_session,
        user,
    )

    assert p1.version == 1
    assert p2.version == 2
    assert p1.pack_id != p2.pack_id


# ------------------------------------------------------------------
# Integrity verification
# ------------------------------------------------------------------


@pytest.mark.unit
def test_integrity_hash_verifiable(db_session, case_with_finding):
    """Hash in the pack can be verified by re-computing from snapshot."""
    case = case_with_finding
    user = _FakeUser()

    created = ep_api.create_evidence_pack(
        case.case_id,
        EvidencePackCreateRequest(format="json"),
        db_session,
        user,
    )

    detail = ep_api.get_evidence_pack(
        case.case_id,
        created.pack_id,
        db_session,
        user,
    )

    snapshot_copy = json.loads(json.dumps(detail.snapshot_json, default=str))
    snapshot_copy["integrity"]["content_hash"] = ""
    canonical = EvidencePackBuilder.canonicalize(snapshot_copy)
    recomputed = EvidencePackBuilder.compute_hash(canonical)

    assert recomputed == created.integrity_hash


# ------------------------------------------------------------------
# Download audit event
# ------------------------------------------------------------------


@pytest.mark.unit
def test_download_records_audit_event(db_session, case_with_finding):
    """Downloading a pack records an evidence_pack.downloaded event."""
    case = case_with_finding
    user = _FakeUser()

    created = ep_api.create_evidence_pack(
        case.case_id,
        EvidencePackCreateRequest(format="json"),
        db_session,
        user,
    )

    ep_api.download_evidence_pack(
        case.case_id,
        created.pack_id,
        db_session,
        user,
    )

    db_session.flush()
    events = (
        db_session.query(EventRecord)
        .filter(
            EventRecord.event_type == "evidence_pack.downloaded",
            EventRecord.entity_id == created.pack_id,
        )
        .all()
    )
    assert len(events) >= 1
    assert events[0].payload["actor"] == "test-auditor"
