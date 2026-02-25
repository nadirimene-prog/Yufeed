import pytest
from types import SimpleNamespace

from src.ai.impact_analyzer import ImpactAnalyzer


@pytest.mark.unit
def test_impact_analyzer_fallback_and_prompt():
    analyzer = ImpactAnalyzer()
    analyzer.client = None

    doc = {
        "celex": "CELEX-IMPACT",
        "title": "AML Regulation",
        "type": "regulation",
        "compliance_domain": "aml",
        "risk_level": "high",
    }

    prompt = analyzer._build_impact_prompt(doc)
    assert "AML Regulation" in prompt
    assert "CELEX-IMPACT" in prompt

    analysis = analyzer.analyze_impact(doc)
    assert analysis["overall_impact_level"] == "high"
    assert analysis["affected_areas"]
    assert analysis["resource_estimates"]["requires_process_changes"] is True


@pytest.mark.unit
def test_impact_analyzer_parse_response_and_fallback_structure():
    analyzer = ImpactAnalyzer()

    response_text = """
    ```json
    {
      "overall_impact_level": "low",
      "executive_summary": "Short summary",
      "affected_areas": ["onboarding"],
      "key_changes": ["Change A"],
      "action_items": [],
      "gaps": [],
      "resource_estimates": {"total_hours": 5, "total_cost_eur": 1000}
    }
    ```
    """

    parsed = analyzer._parse_impact_response(response_text)
    assert parsed["overall_impact_level"] == "low"
    assert parsed["affected_areas"] == ["onboarding"]

    fallback = analyzer._fallback_analysis_structure()
    assert fallback["overall_impact_level"] == "medium"
    assert "resource_estimates" in fallback


@pytest.mark.unit
def test_impact_analyzer_retries_retryable_anthropic_error(monkeypatch):
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
    monkeypatch.setattr("src.ai.impact_analyzer.time.sleep", lambda *_args, **_kwargs: None)

    analyzer = ImpactAnalyzer()
    analyzer.client = SimpleNamespace(messages=FakeMessages())

    result = analyzer._call_claude_with_retry(model="claude-sonnet-4-20250514")

    assert result is analyzer.client.messages.response
    assert analyzer.client.messages.calls == 2


@pytest.mark.unit
def test_impact_analyzer_repairs_malformed_json(monkeypatch):
    class FakeResponse:
        def __init__(self, text: str):
            self.content = [SimpleNamespace(text=text)]

    responses = [
        FakeResponse('{"overall_impact_level":"high","executive_summary":"x",}'),
        FakeResponse(
            """
            {
              "overall_impact_level": "high",
              "executive_summary": "Short summary",
              "affected_areas": ["onboarding"],
              "key_changes": ["Change A"],
              "action_items": [],
              "gaps": [],
              "resource_estimates": {"total_hours": 5, "total_cost_eur": 1000}
            }
            """
        ),
    ]
    call_count = {"n": 0}

    def fake_call(**kwargs):
        result = responses[call_count["n"]]
        call_count["n"] += 1
        return result

    analyzer = ImpactAnalyzer()
    analyzer.client = object()
    monkeypatch.setattr(analyzer, "_call_claude_with_retry", fake_call)

    doc = {
        "celex": "CELEX-IMPACT",
        "title": "AML Regulation",
        "type": "regulation",
        "compliance_domain": "aml",
    }
    analysis = analyzer.analyze_impact(doc)

    assert analysis["overall_impact_level"] == "high"
    assert analysis["affected_areas"] == ["onboarding"]
    assert call_count["n"] == 2


@pytest.mark.unit
def test_impact_analyzer_repairs_schema_invalid_json(monkeypatch):
    class FakeResponse:
        def __init__(self, text: str):
            self.content = [SimpleNamespace(text=text)]

    responses = [
        FakeResponse(
            """
            {
              "overall_impact_level": "urgent",
              "executive_summary": "Short summary",
              "affected_areas": "onboarding",
              "key_changes": ["Change A"],
              "action_items": [],
              "gaps": [],
              "resource_estimates": {"total_hours": 5, "total_cost_eur": 1000}
            }
            """
        ),
        FakeResponse(
            """
            {
              "overall_impact_level": "high",
              "executive_summary": "Short summary",
              "affected_areas": ["onboarding"],
              "key_changes": ["Change A"],
              "action_items": [],
              "gaps": [],
              "resource_estimates": {"total_hours": 5, "total_cost_eur": 1000}
            }
            """
        ),
    ]
    call_count = {"n": 0}

    def fake_call(**kwargs):
        result = responses[call_count["n"]]
        call_count["n"] += 1
        return result

    analyzer = ImpactAnalyzer()
    analyzer.client = object()
    monkeypatch.setattr(analyzer, "_call_claude_with_retry", fake_call)

    doc = {
        "celex": "CELEX-IMPACT",
        "title": "AML Regulation",
        "type": "regulation",
        "compliance_domain": "aml",
    }
    analysis = analyzer.analyze_impact(doc)

    assert analysis["overall_impact_level"] == "high"
    assert analysis["affected_areas"] == ["onboarding"]
    assert call_count["n"] == 2
