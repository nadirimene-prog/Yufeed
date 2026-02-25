import pytest
from starlette.background import BackgroundTasks

from src.api import ai_agents as ai_agents_api
from src.models.transaction_models import Alert
from tests.factories.transaction_factories import AlertFactory


@pytest.mark.unit
def test_batch_triage_alerts_selected_mode_queues_helper(db_session, monkeypatch):
    a1 = AlertFactory(sqlalchemy_session=db_session, status="pending", tenant_id="default")
    a2 = AlertFactory(sqlalchemy_session=db_session, status="pending", tenant_id="default")

    published = {}
    monkeypatch.setattr(
        ai_agents_api,
        "publish_event_safe",
        lambda *_args, **kwargs: published.update(kwargs.get("payload", {})),
    )

    bg = BackgroundTasks()
    payload = ai_agents_api.BatchTriageRequest(alert_ids=[a1.id, a2.id], limit=99)
    result = ai_agents_api.batch_triage_alerts(payload, bg, db_session)

    assert result["status"] == "started"
    assert result["mode"] == "selected_ids"
    assert result["requested_count"] == 2
    assert result["processed_target"] == 2
    assert len(bg.tasks) == 1
    task = bg.tasks[0]
    assert task.func is ai_agents_api._batch_triage_selected_task
    assert task.args == ([a1.id, a2.id],)


@pytest.mark.unit
def test_batch_triage_alerts_pending_mode_queues_pending_helper(db_session, monkeypatch):
    monkeypatch.setattr(ai_agents_api, "publish_event_safe", lambda *args, **kwargs: None)

    bg = BackgroundTasks()
    payload = ai_agents_api.BatchTriageRequest(limit=12)
    result = ai_agents_api.batch_triage_alerts(payload, bg, db_session)

    assert result["mode"] == "pending_limit"
    assert result["requested_count"] is None
    assert result["processed_target"] == 12
    assert len(bg.tasks) == 1
    assert bg.tasks[0].func is ai_agents_api._batch_triage_pending_task
    assert bg.tasks[0].args == (12,)


@pytest.mark.unit
def test_batch_enrich_alerts_queues_helper(db_session, monkeypatch):
    alert = AlertFactory(sqlalchemy_session=db_session, status="pending", tenant_id="default")
    monkeypatch.setattr(ai_agents_api, "publish_event_safe", lambda *args, **kwargs: None)

    bg = BackgroundTasks()
    result = ai_agents_api.batch_enrich_alerts([alert.id], bg, db_session)

    assert result["status"] == "started"
    assert result["alert_count"] == 1
    assert len(bg.tasks) == 1
    assert bg.tasks[0].func is ai_agents_api._batch_enrich_alerts_task
    assert bg.tasks[0].args == ([alert.id],)


@pytest.mark.unit
def test_batch_triage_alerts_selected_mode_404_on_missing_alert(db_session, monkeypatch):
    monkeypatch.setattr(ai_agents_api, "publish_event_safe", lambda *args, **kwargs: None)
    bg = BackgroundTasks()

    with pytest.raises(ai_agents_api.HTTPException) as exc:
        ai_agents_api.batch_triage_alerts(
            ai_agents_api.BatchTriageRequest(alert_ids=[999999]),
            bg,
            db_session,
        )

    assert exc.value.status_code == 404
