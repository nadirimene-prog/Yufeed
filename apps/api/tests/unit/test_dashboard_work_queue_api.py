from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from src.api import dashboard_work_queue as queue_api
from src.models.case_decision import CaseDecision
from src.models.tenant_models import Tenant, TenantUser
from src.models.transaction_models import Alert, Case, Transaction
from src.schemas.dashboard_v3 import (
    DashboardWorkQueueResponse,
    FreshnessMeta,
    WorkItemActionRequest,
)


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
def test_work_queue_filtering_pagination_and_sorting(db_session):
    now = datetime.now(timezone.utc)

    txn_critical = Transaction(
        tenant_id="default",
        transaction_id="txn_q_critical",
        user_id="user_critical",
        amount=2500,
        currency="EUR",
        transaction_type="transfer",
        timestamp=now - timedelta(hours=1),
        status="flagged",
        country_code="US",
        risk_level="high",
        risk_score=92,
    )
    txn_medium = Transaction(
        tenant_id="default",
        transaction_id="txn_q_medium",
        user_id="user_medium",
        amount=320,
        currency="EUR",
        transaction_type="payment",
        timestamp=now - timedelta(hours=2),
        status="completed",
        country_code="FR",
        risk_level="medium",
        risk_score=42,
    )

    alert_critical = Alert(
        tenant_id="default",
        alert_id="alert_q_critical",
        alert_type="sanctions_screening",
        severity="critical",
        transaction=txn_critical,
        user_id="user_critical",
        status="pending",
        priority=1,
        risk_score=95,
        created_at=now - timedelta(hours=3),
    )
    alert_medium = Alert(
        tenant_id="default",
        alert_id="alert_q_medium",
        alert_type="velocity",
        severity="medium",
        transaction=txn_medium,
        user_id="user_medium",
        status="pending",
        priority=3,
        risk_score=44,
        created_at=now - timedelta(minutes=30),
    )

    case = Case(
        tenant_id="default",
        case_id="CASE-Q-1",
        case_type="investigation",
        subject_type="user",
        subject_id="entity_1",
        status="open",
        priority="high",
        assigned_to="analyst_1",
        opened_at=now - timedelta(hours=12),
        related_transaction_ids=[],
    )

    db_session.add_all([txn_critical, txn_medium, alert_critical, alert_medium, case])
    db_session.commit()
    db_session.refresh(case)

    approval = CaseDecision(
        tenant_id="default",
        case_id=case.id,
        status="submitted",
        disposition="sar_required",
        rationale="Needs approval",
        created_by="analyst_1",
        submitted_at=now - timedelta(minutes=25),
    )
    db_session.add(approval)
    db_session.commit()

    current_user = _FakeUser(user_id="analyst_1")

    page_one = queue_api.get_dashboard_work_queue(
        page=1,
        page_size=2,
        queue="all",
        severity=None,
        jurisdiction=None,
        sla=None,
        search=None,
        saved_view=None,
        db=db_session,
        current_user=current_user,
    )
    page_two = queue_api.get_dashboard_work_queue(
        page=2,
        page_size=2,
        queue="all",
        severity=None,
        jurisdiction=None,
        sla=None,
        search=None,
        saved_view=None,
        db=db_session,
        current_user=current_user,
    )

    assert page_one.total >= 4
    assert len(page_one.items) == 2
    assert page_one.freshness is not None
    assert page_one.freshness.stale_after_seconds == 60
    assert page_one.items[0].severity in {"critical", "high"}
    assert page_one.items[0].sla_status in {"breached", "warning"}
    assert {item.item_id for item in page_one.items}.isdisjoint(
        {item.item_id for item in page_two.items}
    )

    critical_only = queue_api.get_dashboard_work_queue(
        page=1,
        page_size=50,
        queue="all",
        severity="critical",
        jurisdiction=None,
        sla=None,
        search=None,
        saved_view=None,
        db=db_session,
        current_user=current_user,
    )
    assert critical_only.total >= 1
    assert all(item.severity == "critical" for item in critical_only.items)

    approval_queue = queue_api.get_dashboard_work_queue(
        page=1,
        page_size=50,
        queue="approvals",
        severity=None,
        jurisdiction=None,
        sla=None,
        search=None,
        saved_view=None,
        db=db_session,
        current_user=current_user,
    )
    assert approval_queue.total >= 1
    assert all(item.kind == "approval" for item in approval_queue.items)

    case_queue = queue_api.get_dashboard_work_queue(
        page=1,
        page_size=50,
        queue="cases",
        severity=None,
        jurisdiction=None,
        sla=None,
        search=None,
        saved_view=None,
        db=db_session,
        current_user=current_user,
    )
    assert any(item.entity_type == "user" for item in case_queue.items)

    search_results = queue_api.get_dashboard_work_queue(
        page=1,
        page_size=50,
        queue="all",
        severity=None,
        jurisdiction=None,
        sla=None,
        search="alert_q_critical",
        saved_view=None,
        db=db_session,
        current_user=current_user,
    )
    assert search_results.total >= 1
    assert any("alert_q_critical" in item.ref_id for item in search_results.items)

    detail = queue_api.get_work_item_detail(
        kind="alert",
        item_id=str(alert_critical.id),
        db=db_session,
        current_user=current_user,
    )
    assert detail.freshness is not None
    assert detail.freshness.stale_after_seconds == 30
    assert detail.decision_trace is not None
    assert detail.review_provenance is not None


@pytest.mark.unit
def test_work_item_actions_are_recorded_in_event_backed_detail_history(db_session):
    now = datetime.now(timezone.utc)
    txn = Transaction(
        tenant_id="default",
        transaction_id="txn_q_events",
        user_id="user_events",
        amount=1400,
        currency="USD",
        transaction_type="transfer",
        timestamp=now - timedelta(hours=1),
        status="flagged",
        country_code="US",
        risk_level="medium",
        risk_score=65,
    )
    alert = Alert(
        tenant_id="default",
        alert_id="alert_q_events",
        alert_type="velocity",
        severity="medium",
        transaction=txn,
        user_id="user_events",
        status="pending",
        priority=3,
        risk_score=65,
        created_at=now - timedelta(minutes=30),
    )
    db_session.add_all([txn, alert])
    db_session.commit()

    current_user = _FakeUser(user_id="analyst_events")
    queue_api.perform_work_item_action(
        kind="alert",
        item_id=str(alert.id),
        payload=WorkItemActionRequest(action="mark_in_progress"),
        db=db_session,
        current_user=current_user,
    )

    detail = queue_api.get_work_item_detail(
        kind="alert",
        item_id=str(alert.id),
        db=db_session,
        current_user=current_user,
    )

    assert any(
        item.action == "dashboard.alert.marked_in_progress" for item in detail.action_history
    )
    assert any(
        "Marked In Progress" in event.label or event.label == "Alert Marked In Progress"
        for event in detail.context_timeline
    )
    assert all(event.label != "Last update" for event in detail.context_timeline)
    assert all(event.label != "Alert created" for event in detail.context_timeline)
    assert detail.decision_trace is not None
    assert detail.decision_trace.human_decision == "mark_in_progress"


@pytest.mark.unit
def test_alert_detail_ai_recommendation_uses_ml_fields_when_present(db_session):
    now = datetime.now(timezone.utc)
    txn = Transaction(
        tenant_id="default",
        transaction_id="txn_q_ml_ai",
        user_id="user_ml_ai",
        amount=2100,
        currency="USD",
        transaction_type="transfer",
        timestamp=now - timedelta(hours=1),
        status="flagged",
        country_code="US",
        risk_level="high",
        risk_score=88,
    )
    alert = Alert(
        tenant_id="default",
        alert_id="alert_q_ml_ai",
        alert_type="velocity",
        severity="high",
        transaction=txn,
        user_id="user_ml_ai",
        status="pending",
        priority=2,
        risk_score=88,
        created_at=now - timedelta(minutes=40),
        ml_prediction="true_positive",
        ml_confidence=Decimal("0.93"),
        ml_model_version="triage-v2",
    )
    db_session.add_all([txn, alert])
    db_session.commit()

    detail = queue_api.get_work_item_detail(
        kind="alert",
        item_id=str(alert.id),
        db=db_session,
        current_user=_FakeUser(user_id="analyst_ml"),
    )

    assert "true-positive risk" in detail.ai_recommendation.summary.lower()
    assert detail.ai_recommendation.confidence == pytest.approx(0.93, abs=1e-6)
    assert any(
        reason == "ml_prediction=true_positive" for reason in detail.ai_recommendation.rationale
    )
    assert any(
        reason == "ml_model_version=triage-v2" for reason in detail.ai_recommendation.rationale
    )


@pytest.mark.unit
def test_alert_detail_ai_recommendation_falls_back_without_ml_fields(db_session):
    now = datetime.now(timezone.utc)
    txn = Transaction(
        tenant_id="default",
        transaction_id="txn_q_ml_fallback",
        user_id="user_ml_fallback",
        amount=900,
        currency="USD",
        transaction_type="payment",
        timestamp=now - timedelta(hours=1),
        status="flagged",
        country_code="US",
        risk_level="medium",
        risk_score=41,
    )
    alert = Alert(
        tenant_id="default",
        alert_id="alert_q_ml_fallback",
        alert_type="velocity",
        severity="medium",
        transaction=txn,
        user_id="user_ml_fallback",
        status="pending",
        priority=3,
        risk_score=41,
        created_at=now - timedelta(minutes=25),
        ml_prediction=None,
        ml_confidence=None,
    )
    db_session.add_all([txn, alert])
    db_session.commit()

    detail = queue_api.get_work_item_detail(
        kind="alert",
        item_id=str(alert.id),
        db=db_session,
        current_user=_FakeUser(user_id="analyst_ml_fallback"),
    )

    assert "analyst triage" in detail.ai_recommendation.summary.lower()
    assert detail.ai_recommendation.confidence == pytest.approx(0.74, abs=1e-6)
    assert all(
        not reason.startswith("ml_prediction=") for reason in detail.ai_recommendation.rationale
    )


@pytest.mark.unit
def test_review_event_persists_decision_trace_for_alert(db_session):
    now = datetime.now(timezone.utc)
    txn = Transaction(
        tenant_id="default",
        transaction_id="txn_q_review_trace",
        user_id="user_review_trace",
        amount=1200,
        currency="USD",
        transaction_type="transfer",
        timestamp=now - timedelta(hours=1),
        status="flagged",
        country_code="US",
        risk_level="high",
        risk_score=83,
    )
    alert = Alert(
        tenant_id="default",
        alert_id="alert_q_review_trace",
        alert_type="sanctions_screening",
        severity="high",
        transaction=txn,
        user_id="user_review_trace",
        status="in_review",
        priority=2,
        risk_score=83,
        created_at=now - timedelta(hours=3),
        assigned_to="maker_user",
    )
    db_session.add_all([txn, alert])
    db_session.commit()

    reviewer = _FakeUser(user_id="reviewer_user")
    queue_api.review_work_item(
        kind="alert",
        item_id=str(alert.id),
        payload=queue_api.ReviewActionRequest(
            proposed_action="close",
            decision="approve",
            submitted_by="maker_user",
            review_notes="approved after independent review",
            sar_required=False,
        ),
        db=db_session,
        current_user=reviewer,
    )

    detail = queue_api.get_work_item_detail(
        kind="alert",
        item_id=str(alert.id),
        db=db_session,
        current_user=reviewer,
    )
    assert detail.decision_trace is not None
    assert detail.decision_trace.human_decision == "approve"
    assert detail.decision_trace.override_reason == "approved after independent review"


@pytest.mark.unit
def test_reg_task_evidence_reflects_persisted_sar_template_state(db_session):
    now = datetime.now(timezone.utc)
    case_without_template = Case(
        tenant_id="default",
        case_id="CASE-REG-NO-TEMPLATE",
        case_type="sar_preparation",
        subject_type="user",
        subject_id="entity_reg_1",
        status="open",
        priority="high",
        outcome="sar_required",
        opened_at=now - timedelta(hours=10),
        evidence={},
    )
    case_with_template = Case(
        tenant_id="default",
        case_id="CASE-REG-WITH-TEMPLATE",
        case_type="sar_preparation",
        subject_type="user",
        subject_id="entity_reg_2",
        status="open",
        priority="high",
        outcome="sar_required",
        opened_at=now - timedelta(hours=10),
        evidence={
            "sar_id": "SAR-20260227-001",
            "sar_draft": {"sar_id": "SAR-20260227-001", "narrative": "Draft ready"},
            "sar_lifecycle": {"current_status": "draft"},
        },
    )
    db_session.add_all([case_without_template, case_with_template])
    db_session.commit()

    current_user = _FakeUser(user_id="analyst_reg_task")
    detail_without_template = queue_api.get_work_item_detail(
        kind="reg_task",
        item_id=str(case_without_template.id),
        db=db_session,
        current_user=current_user,
    )
    detail_with_template = queue_api.get_work_item_detail(
        kind="reg_task",
        item_id=str(case_with_template.id),
        db=db_session,
        current_user=current_user,
    )

    checklist_without_template = {
        item.id: item.completed for item in detail_without_template.evidence_checklist
    }
    checklist_with_template = {
        item.id: item.completed for item in detail_with_template.evidence_checklist
    }
    assert checklist_without_template.get("sar-template") is False
    assert checklist_with_template.get("sar-template") is True


@pytest.mark.unit
def test_workspace_users_endpoint_respects_tenant_scope(db_session):
    tenant = Tenant(tenant_id="tenant-workspace", name="Workspace Tenant")
    db_session.add(tenant)
    db_session.flush()

    user_a = TenantUser(
        tenant_id=tenant.id,
        user_id="analyst_a",
        role="analyst",
        is_active=True,
    )
    user_b = TenantUser(
        tenant_id=tenant.id,
        user_id="analyst_b",
        role="reviewer",
        is_active=False,
    )
    db_session.add_all([user_a, user_b])
    db_session.commit()

    current_user = _FakeUser(tenant_id="tenant-workspace")

    active_users = queue_api._list_workspace_users(
        tenant_id=None,
        is_active=True,
        db=db_session,
        current_user=current_user,
    )
    inactive_users = queue_api._list_workspace_users(
        tenant_id=None,
        is_active=False,
        db=db_session,
        current_user=current_user,
    )

    assert [user.user_id for user in active_users] == ["analyst_a"]
    assert [user.user_id for user in inactive_users] == ["analyst_b"]


@pytest.mark.unit
def test_work_queue_uses_stage1_for_non_alert_jurisdiction_filter(db_session, monkeypatch):
    called = {"stage1": False}

    def _fake_stage1(**kwargs):
        called["stage1"] = True
        return DashboardWorkQueueResponse(
            page=kwargs["page"],
            page_size=kwargs["page_size"],
            total=0,
            items=[],
            freshness=FreshnessMeta(
                generated_at=datetime.now(timezone.utc),
                stale_after_seconds=60,
            ),
        )

    monkeypatch.setattr(queue_api, "_get_dashboard_work_queue_stage1", _fake_stage1)

    queue_api.get_dashboard_work_queue(
        page=1,
        page_size=25,
        queue="cases",
        severity=None,
        jurisdiction="US",
        sla=None,
        search=None,
        saved_view=None,
        db=db_session,
        current_user=_FakeUser(),
    )

    assert called["stage1"] is True
