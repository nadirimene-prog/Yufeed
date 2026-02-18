from datetime import datetime, timedelta, timezone

import pytest

from src.api import dashboard_work_queue as queue_api
from src.models.case_decision import CaseDecision
from src.models.transaction_models import Alert, Case, Transaction


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
