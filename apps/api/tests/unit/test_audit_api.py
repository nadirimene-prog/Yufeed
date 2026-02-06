import pytest
from datetime import datetime, timezone

from src.api import audit as audit_api
from src.audit.models import AuditLog
from src.auth.dependencies import CurrentUser
from src.schemas.audit_schemas import EventCreate, DecisionCreate


@pytest.mark.unit
def test_audit_event_and_decision_flow(db_session):
    current_user = CurrentUser(
        user_id="user-1",
        email="user@example.com",
        role="admin",
        tenant_id="default",
        is_superuser=False,
    )
    log = AuditLog(
        audit_id="audit-test-1",
        tenant_id="default",
        actor_id="user-1",
        actor_email="user@example.com",
        actor_role="admin",
        action="create",
        method="POST",
        path="/api/test",
        entity_type="alert",
        entity_id="alert-1",
        status_code=200,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(log)
    db_session.commit()

    logs = audit_api.list_audit_logs_compat(
        skip=0,
        limit=100,
        actor_id=None,
        entity_type=None,
        entity_id=None,
        action=None,
        db=db_session,
        current_user=current_user,
    )
    assert logs

    direct_logs = audit_api.list_audit_logs(
        skip=0,
        limit=100,
        actor_id="user-1",
        entity_type=None,
        entity_id=None,
        action=None,
        db=db_session,
        current_user=current_user,
    )
    assert direct_logs

    fetched = audit_api.get_audit_log("audit-test-1", db_session, current_user)
    assert fetched.audit_id == "audit-test-1"

    event = audit_api.create_event(
        EventCreate(
            event_type="alert.created",
            entity_type="alert",
            entity_id="alert-1",
            source="tests",
            payload={"foo": "bar"},
        ),
        db_session,
        current_user,
    )
    assert event.event_id

    event_get = audit_api.get_event(event.event_id, db_session, current_user)
    assert event_get.event_id == event.event_id

    decision = audit_api.create_decision(
        DecisionCreate(
            decision="alert",
            reason_codes=["RULE-1"],
            event_id=event.event_id,
            evidence={"risk_score": 50},
        ),
        db_session,
        current_user,
    )
    assert decision.decision_id

    decision_get = audit_api.get_decision(decision.decision_id, db_session, current_user)
    assert decision_get.decision_id == decision.decision_id

    decisions = audit_api.list_decisions(
        skip=0,
        limit=50,
        decision="alert",
        event_type="alert.created",
        entity_type="alert",
        entity_id="alert-1",
        event_id=event.event_id,
        decision_id=None,
        created_from=None,
        created_to=None,
        db=db_session,
        current_user=current_user,
    )
    assert decisions.total >= 1
