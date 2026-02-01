import pytest

from src.ai.alert_triage import AlertTriageAgent


@pytest.mark.unit
def test_alert_triage_fallback(db_session, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    agent = AlertTriageAgent(db_session)
    result = agent.triage_alert(alert_id=1)

    assert result["recommendation"] == "investigate"
    assert result["confidence"] == 0.5


@pytest.mark.unit
def test_alert_triage_helpers(db_session, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    agent = AlertTriageAgent(db_session)

    evidence = agent._format_evidence({"key": "value"})
    assert "key" in evidence

    formatted = agent._format_list(["a", "b"])
    assert "- a" in formatted

    assert agent._format_list([]) == "None"


@pytest.mark.unit
def test_alert_triage_batch_no_client(db_session, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    agent = AlertTriageAgent(db_session)
    assert agent.batch_triage_pending_alerts() == []
