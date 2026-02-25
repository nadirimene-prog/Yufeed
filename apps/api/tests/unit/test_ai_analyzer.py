import pytest
from datetime import datetime, timezone

from src.ai import analyzer as ai_analyzer
from src.models.models import ComplianceDomain, RiskLevel


@pytest.mark.unit
def test_analyzer_fallback_classification_and_risk(monkeypatch):
    monkeypatch.setattr(ai_analyzer, "client", None)

    aml_title = "Anti Money Laundering Regulation"
    payment_title = "Payment Services Directive"
    misc_title = "Administrative Notice"

    assert ai_analyzer.classify_document(aml_title, "CELEX1") == ComplianceDomain.AML.value
    assert ai_analyzer.classify_document(payment_title, "CELEX2") == ComplianceDomain.PAYMENTS.value
    assert ai_analyzer.classify_document(misc_title, "CELEX3") == ComplianceDomain.OTHER.value

    assert ai_analyzer.assess_risk_level(aml_title, "CELEX1") == RiskLevel.HIGH.value
    assert ai_analyzer.assess_risk_level(payment_title, "CELEX2") == RiskLevel.MEDIUM.value
    assert ai_analyzer.assess_risk_level(misc_title, "CELEX3") == RiskLevel.LOW.value


@pytest.mark.unit
def test_analyzer_text_helpers_and_deadline(monkeypatch):
    monkeypatch.setattr(ai_analyzer, "client", None)

    assert ai_analyzer._truncate_text("", 10) == ""
    assert ai_analyzer._truncate_text("short", 10) == "short"
    assert ai_analyzer._truncate_text("one two three four", 7) == "one..."

    articles = [
        {"number": "1", "title": "Scope", "content": "Banks shall comply with obligations."},
        {"number": "2", "title": "Requirements", "content": "Entities must perform checks."},
    ]
    excerpts = ai_analyzer._select_article_excerpts(articles)
    assert excerpts
    assert "Article 1" in excerpts[0] or "Article 2" in excerpts[0]

    pub_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
    deadline = ai_analyzer.extract_deadline("Directive on Compliance", pub_date)
    assert deadline.year == 2026


@pytest.mark.unit
def test_analyzer_full_analysis_fallback(monkeypatch):
    monkeypatch.setattr(ai_analyzer, "client", None)

    result = ai_analyzer.analyze_document(
        {
            "celex": "CELEX-TEST",
            "title": "AML Regulation",
            "publication_date": datetime(2024, 6, 1, tzinfo=timezone.utc),
            "full_text": "This regulation establishes AML rules.",
            "article_breakdown": [{"number": "1", "content": "Banks shall..."}],
        }
    )

    assert result["compliance_domain"] == ComplianceDomain.AML.value
    assert result["risk_level"] in {
        RiskLevel.HIGH.value,
        RiskLevel.MEDIUM.value,
        RiskLevel.LOW.value,
    }
    assert "analyzed_at" in result
    assert result["usage_events"] == []
    assert result["usage_summary"]["calls"] == 0
    assert result["usage_summary"]["providers"] == []


@pytest.mark.unit
def test_extract_obligations_parses_markdown_fences(monkeypatch):
    class DummyChunk:
        def __init__(self, text: str):
            self.text = text

    class DummyMessage:
        def __init__(self, text: str):
            self.content = [DummyChunk(text)]

    class DummyMessages:
        def create(self, *args, **kwargs):
            return DummyMessage(
                "```json\n"
                "[\n"
                '  {"obligation": "Banks shall maintain records", "article": "Article 1", "deadline": null, "applicability": "banks", "source_excerpt": "Banks shall..."}\n'
                "]\n"
                "```"
            )

    class DummyClient:
        def __init__(self):
            self.messages = DummyMessages()

    monkeypatch.setattr(ai_analyzer, "client", DummyClient())
    monkeypatch.setattr(ai_analyzer, "ANTHROPIC_DISABLED_REASON", None)

    out = ai_analyzer.extract_obligations(
        "Test Regulation",
        "CELEX-TEST",
        full_text="Article 1 Banks shall maintain records.",
        article_breakdown=None,
    )
    assert isinstance(out, list)
    assert out
    assert out[0]["obligation"] == "Banks shall maintain records"


@pytest.mark.unit
def test_analyzer_collects_usage_events_for_anthropic_calls(monkeypatch):
    class DummyUsage:
        input_tokens = 10
        output_tokens = 5
        cache_creation_input_tokens = 0
        cache_read_input_tokens = 0

    class DummyChunk:
        def __init__(self, text: str):
            self.text = text

    class DummyMessage:
        def __init__(self, text: str, model: str = "claude-3-haiku-20240307"):
            self.content = [DummyChunk(text)]
            self.usage = DummyUsage()
            self.model = model
            self.id = "msg_test"
            self.stop_reason = "end_turn"

    class DummyMessages:
        def create(self, *args, **kwargs):
            prompt = kwargs["messages"][0]["content"]
            if "Classify this EU legal document" in prompt:
                return DummyMessage("aml")
            if "Assess the compliance risk level" in prompt:
                return DummyMessage("high")
            if "Extract the key compliance obligations" in prompt:
                return DummyMessage(
                    '[{"obligation":"Banks shall maintain records","article":"Article 1","deadline":null,"applicability":"banks","source_excerpt":"Banks shall maintain records"}]'
                )
            if "Extract the implementation/transposition deadline" in prompt:
                return DummyMessage("none")
            if "Create a concise executive summary" in prompt:
                return DummyMessage("Short summary")
            raise AssertionError(f"Unexpected prompt: {prompt[:120]}")

    class DummyClient:
        def __init__(self):
            self.messages = DummyMessages()

    monkeypatch.setattr(ai_analyzer, "client", DummyClient())
    monkeypatch.setattr(ai_analyzer, "ANTHROPIC_DISABLED_REASON", None)
    monkeypatch.setattr(ai_analyzer, "OPENAI_DISABLED_REASON", "disabled-for-test")

    result = ai_analyzer.analyze_document(
        {
            "celex": "CELEX-TEST",
            "title": "AML Regulation",
            "publication_date": datetime(2024, 6, 1, tzinfo=timezone.utc),
            "full_text": "Banks shall maintain records.",
            "article_breakdown": [{"number": "1", "content": "Banks shall maintain records."}],
        }
    )

    ops = [event["operation"] for event in result["usage_events"]]
    assert "document_analysis.classify" in ops
    assert "document_analysis.assess_risk" in ops
    assert "document_analysis.extract_obligations" in ops
    assert "document_analysis.extract_deadline" in ops
    assert "document_analysis.generate_summary" in ops
    assert result["usage_summary"]["calls"] >= 5
    assert "anthropic" in result["usage_summary"]["providers"]
