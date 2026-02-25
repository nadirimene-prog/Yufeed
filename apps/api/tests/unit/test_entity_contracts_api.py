from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from src.api import entities as entities_api
from src.api import aml_officer as aml_officer_api
from src.models.compliance import KYCProfile
from src.models.transaction_models import Alert, Case, Transaction, UserRiskProfile


class _FakeUser:
    def __init__(
        self,
        user_id: str = "analyst_1",
        email: str = "analyst@yufeed.local",
        role: str = "compliance",
        tenant_id: str = "default",
    ):
        self.user_id = user_id
        self.email = email
        self.role = role
        self.tenant_id = tenant_id
        self.is_superuser = False


@pytest.mark.unit
def test_list_cases_supports_subject_id_filter(client, auth_headers, db_session):
    now = datetime.now(timezone.utc)

    case_one = Case(
        tenant_id="default",
        case_id="CASE-SUBJECT-001",
        case_type="investigation",
        subject_type="user",
        subject_id="user-entity-1",
        status="open",
        priority="high",
        opened_at=now,
    )
    case_two = Case(
        tenant_id="default",
        case_id="CASE-SUBJECT-002",
        case_type="investigation",
        subject_type="user",
        subject_id="user-entity-2",
        status="open",
        priority="medium",
        opened_at=now,
    )
    db_session.add_all([case_one, case_two])
    db_session.commit()

    response = client.get(
        "/api/cases/?subject_id=user-entity-1",
        headers=auth_headers,
    )

    assert response.status_code == 200
    filtered = response.json()
    assert len(filtered) == 1
    assert filtered[0]["case_id"] == "CASE-SUBJECT-001"


@pytest.mark.unit
def test_entity_profile_aggregates_risk_compliance_alerts_cases_and_transactions(db_session):
    now = datetime.now(timezone.utc)

    profile = KYCProfile(
        tenant_id="default",
        user_id="entity-user-1",
        first_name="Entity",
        last_name="User",
        email="entity.user@example.com",
        status="pending",
        risk_level="high",
        created_at=now,
        updated_at=now,
    )
    db_session.add(profile)
    db_session.flush()

    risk = UserRiskProfile(
        tenant_id="default",
        user_id="entity-user-1",
        compliance_profile_id=profile.id,
        overall_risk_score=87,
        risk_level="high",
        kyc_status="pending_review",
        enhanced_due_diligence=True,
        updated_at=now,
    )
    transaction = Transaction(
        tenant_id="default",
        transaction_id="TX-ENTITY-001",
        user_id="entity-user-1",
        amount=2500,
        currency="EUR",
        transaction_type="transfer",
        timestamp=now,
        status="flagged",
        country_code="FR",
        risk_score=76,
    )
    alert = Alert(
        tenant_id="default",
        alert_id="ALT-ENTITY-001",
        alert_type="velocity",
        severity="high",
        user_id="entity-user-1",
        transaction=transaction,
        status="pending",
        priority=2,
        risk_score=82,
        rule_id="RULE-ENTITY-001",
        matched_rules_data={"RULE-ENTITY-001": "Velocity Threshold"},
        created_at=now,
        updated_at=now,
    )
    case = Case(
        tenant_id="default",
        case_id="CASE-ENTITY-001",
        case_type="investigation",
        subject_type="user",
        subject_id="entity-user-1",
        status="open",
        priority="high",
        opened_at=now,
        updated_at=now,
    )

    db_session.add_all([risk, transaction, alert, case])
    db_session.commit()

    payload = entities_api.get_entity_profile(
        entity_type="user",
        entity_id="entity-user-1",
        db=db_session,
        current_user=_FakeUser(),
    )

    assert payload["id"] == "entity-user-1"
    assert payload["risk"]["overall_score"] == 87.0
    assert payload["compliance"]["id"] == profile.id
    assert len(payload["alerts"]) == 1
    assert payload["alerts"][0]["triggered_rule_id"] == "RULE-ENTITY-001"
    assert payload["alerts"][0]["triggered_rule_name"] == "Velocity Threshold"
    assert len(payload["cases"]) == 1
    assert payload["cases"][0]["subject_id"] == "entity-user-1"
    assert len(payload["transactions"]) == 1


@pytest.mark.unit
def test_entity_profile_rejects_unsupported_type(db_session):
    with pytest.raises(HTTPException) as exc:
        entities_api.get_entity_profile(
            entity_type="wallet",
            entity_id="abc",
            db=db_session,
            current_user=_FakeUser(),
        )

    assert exc.value.status_code == 400


@pytest.mark.unit
def test_workspace_users_route_is_exposed(client, admin_headers):
    response = client.get("/api/workspace/users", headers=admin_headers)
    assert response.status_code == 200


@pytest.mark.unit
def test_case_comments_threading_contract(client, auth_headers, db_session):
    now = datetime.now(timezone.utc)
    case = Case(
        tenant_id="default",
        case_id="CASE-COMMENT-001",
        case_type="investigation",
        subject_type="user",
        subject_id="comment-user-1",
        status="open",
        priority="medium",
        opened_at=now,
        updated_at=now,
    )
    db_session.add(case)
    db_session.commit()

    root = client.post(
        f"/api/cases/{case.case_id}/comments",
        headers=auth_headers,
        json={"content": "Initial comment for @analyst_2", "mentions": ["analyst_2"]},
    )
    assert root.status_code == 201
    root_payload = root.json()
    assert root_payload["parent_comment_id"] is None
    assert root_payload["mentions"] == ["analyst_2"]

    reply = client.post(
        f"/api/cases/{case.case_id}/comments",
        headers=auth_headers,
        json={
            "content": "Replying on the same thread",
            "parent_comment_id": root_payload["id"],
        },
    )
    assert reply.status_code == 201
    reply_payload = reply.json()
    assert reply_payload["parent_comment_id"] == root_payload["id"]

    listing = client.get(f"/api/cases/{case.case_id}/comments", headers=auth_headers)
    assert listing.status_code == 200
    items = listing.json()
    assert len(items) == 2
    assert any(item["id"] == root_payload["id"] for item in items)
    assert any(item["id"] == reply_payload["id"] for item in items)


@pytest.mark.unit
def test_sar_prepare_returns_and_persists_lifecycle(client, admin_headers, db_session, monkeypatch):
    now = datetime.now(timezone.utc)
    case = Case(
        tenant_id="default",
        case_id="CASE-SAR-LIFECYCLE-001",
        case_type="investigation",
        subject_type="user",
        subject_id="sar-user-1",
        status="open",
        priority="high",
        opened_at=now,
        updated_at=now,
    )
    db_session.add(case)
    db_session.commit()

    class _FakeOfficer:
        async def prepare_sar(self, **kwargs):
            return {
                "narrative": "Generated narrative",
                "filing_reason": "Suspicious structuring pattern",
            }

    monkeypatch.setattr(aml_officer_api, "get_aml_officer", lambda db: _FakeOfficer())
    monkeypatch.setattr(aml_officer_api, "publish_event_safe", lambda *args, **kwargs: None)

    response = client.post(
        "/api/aml-officer/sar/prepare",
        headers=admin_headers,
        json={
            "case_id": case.case_id,
            "case_data": {"subject_id": case.subject_id},
            "related_alerts": [],
            "related_transactions": [],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["sar_id"].startswith("SAR-")
    assert payload["sar_lifecycle"]["current_status"] == "draft"

    db_session.refresh(case)
    assert isinstance(case.evidence, dict)
    assert case.evidence["sar_lifecycle"]["current_status"] == "draft"


@pytest.mark.unit
def test_workflow_execute_populates_agent_context_fields(client, admin_headers, monkeypatch):
    captured = {}

    class _FakeWorkflowResult:
        def to_dict(self):
            return {"success": True, "workflow_id": "wf-1"}

    class _FakeOfficer:
        async def execute_workflow(self, workflow_type, initial_context):
            captured["workflow_type"] = workflow_type
            captured["context"] = initial_context
            return _FakeWorkflowResult()

    monkeypatch.setattr(aml_officer_api, "get_aml_officer", lambda db: _FakeOfficer())

    response = client.post(
        "/api/aml-officer/workflow/execute",
        headers=admin_headers,
        params={"workflow_type": "compliance_qa"},
        json={
            "primary_data": {"question_id": "q1"},
            "input_data": {"action": "answer_question", "question": "What is AMLD6?"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True

    context = captured["context"]
    assert context.tenant_id == "default"
    assert context.user_role == "admin"
    assert context.input_data["action"] == "answer_question"
    assert context.input_data["question"] == "What is AMLD6?"
    assert isinstance(context.session_id, str)
    assert context.session_id
