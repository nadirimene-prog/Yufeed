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
    assert result["risk_level"] in {RiskLevel.HIGH.value, RiskLevel.MEDIUM.value, RiskLevel.LOW.value}
    assert "analyzed_at" in result


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
                "  {\"obligation\": \"Banks shall maintain records\", \"article\": \"Article 1\", \"deadline\": null, \"applicability\": \"banks\", \"source_excerpt\": \"Banks shall...\"}\n"
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
