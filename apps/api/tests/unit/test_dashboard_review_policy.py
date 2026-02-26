from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from src.api import dashboard_work_queue as queue_api
from src.models.transaction_models import Alert, Transaction
from src.schemas.dashboard_v3 import ReviewActionRequest, WorkItemActionRequest


class _FakeUser:
    def __init__(
        self,
        user_id: str,
        email: str = "compliance@yufeed.local",
        role: str = "compliance",
        tenant_id: str = "default",
    ):
        self.user_id = user_id
        self.email = email
        self.role = role
        self.tenant_id = tenant_id
        self.is_superuser = False


@pytest.mark.unit
def test_high_risk_close_requires_review(db_session):
    now = datetime.now(timezone.utc)
    txn = Transaction(
        tenant_id="default",
        transaction_id="txn_review_1",
        user_id="user_review_1",
        amount=5600,
        currency="USD",
        transaction_type="transfer",
        timestamp=now - timedelta(hours=1),
        status="flagged",
        country_code="US",
        risk_level="high",
        risk_score=95,
    )
    alert = Alert(
        tenant_id="default",
        alert_id="alert_review_1",
        alert_type="sanctions",
        severity="critical",
        transaction=txn,
        user_id="user_review_1",
        status="pending",
        priority=1,
        risk_score=95,
        created_at=now - timedelta(hours=3),
    )
    db_session.add_all([txn, alert])
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        queue_api.perform_work_item_action(
            kind="alert",
            item_id=str(alert.id),
            payload=WorkItemActionRequest(action="close", notes="Close directly"),
            db=db_session,
            current_user=_FakeUser(user_id="analyst_1"),
        )

    assert exc_info.value.status_code == 409
    assert "requires reviewer approval" in str(exc_info.value.detail)


@pytest.mark.unit
def test_review_endpoint_blocks_same_user_approval(db_session):
    now = datetime.now(timezone.utc)
    txn = Transaction(
        tenant_id="default",
        transaction_id="txn_review_2",
        user_id="user_review_2",
        amount=4200,
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
        alert_id="alert_review_2",
        alert_type="terrorist_financing",
        severity="high",
        transaction=txn,
        user_id="user_review_2",
        status="pending",
        priority=1,
        risk_score=90,
        created_at=now - timedelta(hours=3),
    )
    db_session.add_all([txn, alert])
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        queue_api.review_work_item(
            kind="alert",
            item_id=str(alert.id),
            payload=ReviewActionRequest(
                proposed_action="close",
                decision="approve",
                submitted_by="analyst_2",
                review_notes="Approved",
            ),
            db=db_session,
            current_user=_FakeUser(user_id="analyst_2"),
        )

    assert exc_info.value.status_code == 409
    assert "4-eyes violation" in str(exc_info.value.detail)


@pytest.mark.unit
def test_review_endpoint_allows_independent_reviewer(db_session):
    now = datetime.now(timezone.utc)
    txn = Transaction(
        tenant_id="default",
        transaction_id="txn_review_3",
        user_id="user_review_3",
        amount=3900,
        currency="EUR",
        transaction_type="payment",
        timestamp=now - timedelta(hours=1),
        status="flagged",
        country_code="DE",
        risk_level="high",
        risk_score=82,
    )
    alert = Alert(
        tenant_id="default",
        alert_id="alert_review_3",
        alert_type="sanctions",
        severity="high",
        transaction=txn,
        user_id="user_review_3",
        status="pending",
        priority=2,
        risk_score=85,
        created_at=now - timedelta(hours=2),
    )
    db_session.add_all([txn, alert])
    db_session.commit()

    response = queue_api.review_work_item(
        kind="alert",
        item_id=str(alert.id),
        payload=ReviewActionRequest(
            proposed_action="close",
            decision="approve",
            submitted_by="analyst_maker",
            review_notes="Reviewed and approved",
        ),
        db=db_session,
        current_user=_FakeUser(user_id="analyst_checker"),
    )

    assert response.success is True
    assert response.review_status == "approved"
    assert response.updated_status == "resolved"
    assert hasattr(response, "next_recommended_item_id")
