import pytest
from datetime import datetime, timezone

from src.api import audit as audit_api
from src.audit.models import AuditLog
from src.schemas.audit_schemas import EventCreate, DecisionCreate


@pytest.mark.unit
def test_audit_event_and_decision_flow(db_session):
    log = AuditLog(
        audit_id="audit-test-1",
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

    logs = audit_api.list_audit_logs_compat(0, 100, None, None, None, None, db_session, None)
    assert logs

    direct_logs = audit_api.list_audit_logs(0, 100, "user-1", None, None, None, db_session, None)
    assert direct_logs

    fetched = audit_api.get_audit_log("audit-test-1", db_session, None)
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
        None,
    )
    assert event.event_id

    event_get = audit_api.get_event(event.event_id, db_session, None)
    assert event_get.event_id == event.event_id

    decision = audit_api.create_decision(
        DecisionCreate(
            decision="alert",
            reason_codes=["RULE-1"],
            event_id=event.event_id,
            evidence={"risk_score": 50},
        ),
        db_session,
        None,
    )
    assert decision.decision_id

    decision_get = audit_api.get_decision(decision.decision_id, db_session, None)
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
        _=None,
    )
    assert decisions.total >= 1
