import pytest
from types import SimpleNamespace

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


@pytest.mark.unit
def test_alert_triage_retries_retryable_anthropic_error(db_session, monkeypatch):
    class RetryableAnthropicError(Exception):
        status_code = 529

    class FakeMessages:
        def __init__(self):
            self.calls = 0
            self.response = object()

        def create(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise RetryableAnthropicError("overloaded_error")
            return self.response

    monkeypatch.setenv("ANTHROPIC_RETRIES", "2")
    monkeypatch.setenv("ANTHROPIC_BACKOFF_SECONDS", "0.01")
    monkeypatch.setenv("ANTHROPIC_JITTER_SECONDS", "0")
    monkeypatch.setattr("src.ai.alert_triage.time.sleep", lambda *_args, **_kwargs: None)

    agent = AlertTriageAgent.__new__(AlertTriageAgent)
    agent.client = SimpleNamespace(messages=FakeMessages())

    result = agent._call_claude_with_retry(model="claude-sonnet-4-20250514")

    assert result is agent.client.messages.response
    assert agent.client.messages.calls == 2


@pytest.mark.unit
def test_alert_triage_repairs_malformed_json(monkeypatch):
    class FakeResponse:
        def __init__(self, text: str):
            self.content = [SimpleNamespace(text=text)]

    calls = []
    responses = [
        FakeResponse('{"recommendation":"investigate","confidence":0.7,}'),
        FakeResponse(
            """
            {
              "recommendation": "investigate",
              "confidence": 0.7,
              "priority": 3,
              "reasoning": "Needs analyst review",
              "true_positive_likelihood": 0.5,
              "investigation_steps": ["Review alert evidence"],
              "regulatory_concerns": "Potential AML relevance",
              "sar_likelihood": 0.2,
              "recommended_actions": ["Escalate for review"],
              "red_flags": [],
              "mitigating_factors": []
            }
            """
        ),
    ]

    def fake_call(**kwargs):
        calls.append(kwargs)
        return responses[len(calls) - 1]

    agent = AlertTriageAgent.__new__(AlertTriageAgent)
    agent._call_claude_with_retry = fake_call

    result = agent._analyze_with_claude("test context")

    assert result["recommendation"] == "investigate"
    assert result["confidence"] == 0.7
    assert len(calls) == 2


@pytest.mark.unit
def test_alert_triage_repairs_schema_invalid_json(monkeypatch):
    class FakeResponse:
        def __init__(self, text: str):
            self.content = [SimpleNamespace(text=text)]

    calls = []
    responses = [
        FakeResponse(
            """
            {
              "recommendation": "urgent",
              "confidence": 1.7,
              "priority": 9,
              "reasoning": "Needs analyst review",
              "true_positive_likelihood": 0.5,
              "investigation_steps": ["Review alert evidence"],
              "regulatory_concerns": "Potential AML relevance",
              "sar_likelihood": 0.2,
              "recommended_actions": ["Escalate for review"],
              "red_flags": [],
              "mitigating_factors": []
            }
            """
        ),
        FakeResponse(
            """
            {
              "recommendation": "investigate",
              "confidence": 0.8,
              "priority": 2,
              "reasoning": "Needs analyst review",
              "true_positive_likelihood": 0.6,
              "investigation_steps": ["Review alert evidence"],
              "regulatory_concerns": "Potential AML relevance",
              "sar_likelihood": 0.2,
              "recommended_actions": ["Escalate for review"],
              "red_flags": [],
              "mitigating_factors": []
            }
            """
        ),
    ]

    def fake_call(**kwargs):
        calls.append(kwargs)
        return responses[len(calls) - 1]

    agent = AlertTriageAgent.__new__(AlertTriageAgent)
    agent._call_claude_with_retry = fake_call

    result = agent._analyze_with_claude("test context")

    assert result["recommendation"] == "investigate"
    assert result["confidence"] == 0.8
    assert result["priority"] == 2
    assert len(calls) == 2
