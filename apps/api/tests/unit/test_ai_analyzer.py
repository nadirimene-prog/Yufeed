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
    assert "obligation_extraction_report" in result
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
def test_extract_obligations_batches_articles_and_dedupes(monkeypatch):
    monkeypatch.setattr(ai_analyzer, "_anthropic_enabled", lambda: True)
    monkeypatch.setattr(ai_analyzer, "_openai_enabled", lambda: False)
    monkeypatch.setattr(
        ai_analyzer.settings, "OBLIGATION_EXTRACTION_SWEEP_ENABLED", False, raising=False
    )

    calls = {"count": 0}

    def fake_extract(prompt: str, max_tokens: int = 3000, timeout_s=None):
        calls["count"] += 1
        assert "Respond with JSON only." in prompt
        if calls["count"] == 1:
            return [
                {
                    "obligation": "Entities shall maintain records.",
                    "article": "Article 1",
                    "source_excerpt": "shall maintain records",
                },
                {
                    "obligation": "Entities must perform screening.",
                    "article": "Article 2",
                    "source_excerpt": "must perform screening",
                },
            ]
        return [
            {
                "obligation": "Entities must perform screening.",
                "article": "Article 2",
                "source_excerpt": "must perform screening",
            },
            {
                "obligation": "Entities shall file reports.",
                "article": "Article 5",
                "source_excerpt": "shall file reports",
            },
        ]

    monkeypatch.setattr(ai_analyzer, "_extract_obligations_with_llm", fake_extract)

    article_breakdown = [
        {"number": "1", "content": "Entities shall maintain records."},
        {"number": "2", "content": "Entities must perform screening."},
        {"number": "3", "content": "Entities shall monitor transactions."},
        {"number": "4", "content": "Entities must train staff."},
        {"number": "5", "content": "Entities shall file reports."},
    ]

    out = ai_analyzer.extract_obligations(
        "AML Regulation",
        "CELEX-AML",
        article_breakdown=article_breakdown,
    )

    assert calls["count"] == 2
    assert len(out) == 3
    assert {item["article"] for item in out} == {"Article 1", "Article 2", "Article 5"}


@pytest.mark.unit
def test_extract_obligations_heuristic_not_capped_at_ten_for_articles(monkeypatch):
    monkeypatch.setattr(ai_analyzer, "_anthropic_enabled", lambda: False)
    monkeypatch.setattr(ai_analyzer, "_openai_enabled", lambda: False)

    article_breakdown = [
        {"number": str(i), "content": f"Entity shall complete control {i}."} for i in range(1, 15)
    ]

    out = ai_analyzer.extract_obligations(
        "Large Regulation",
        "CELEX-LARGE",
        article_breakdown=article_breakdown,
    )

    assert len(out) >= 14


@pytest.mark.unit
def test_extract_obligations_second_pass_sweep_recovers_missed_articles(monkeypatch):
    monkeypatch.setattr(ai_analyzer, "_anthropic_enabled", lambda: True)
    monkeypatch.setattr(ai_analyzer, "_openai_enabled", lambda: False)
    monkeypatch.setattr(
        ai_analyzer.settings, "OBLIGATION_EXTRACTION_SWEEP_ENABLED", True, raising=False
    )

    calls = {"primary": 0, "sweep": 0}

    def fake_extract(prompt: str, max_tokens: int = 3000, timeout_s=None):
        if "Extraction pass: sweep" in prompt:
            calls["sweep"] += 1
            return [
                {
                    "obligation": "Issuers shall maintain records.",
                    "article": "Article 1",
                    "source_excerpt": "shall maintain records",
                },
                {
                    "obligation": "Issuers must notify the authority.",
                    "article": "Article 2",
                    "source_excerpt": "must notify the authority",
                },
            ]
        calls["primary"] += 1
        return []

    monkeypatch.setattr(ai_analyzer, "_extract_obligations_with_llm", fake_extract)
    ai_analyzer._set_obligation_extraction_report(None)

    out = ai_analyzer.extract_obligations(
        "Test Regulation",
        "CELEX-SWEEP",
        article_breakdown=[
            {"number": "1", "content": "Issuers shall maintain records for five years."},
            {"number": "2", "content": "Issuers must notify the authority without delay."},
        ],
    )

    report = ai_analyzer._obligation_extraction_report()

    assert calls["primary"] >= 1
    assert calls["sweep"] >= 1
    assert len(out) == 2
    assert report is not None
    assert report["second_pass_sweep"]["batches_run"] >= 1
    assert report["second_pass_sweep"]["deduped_items_added"] >= 1
    assert report["coverage_after_llm_article_passes"]["covered_signal_article_count"] == 2


@pytest.mark.unit
def test_extract_obligations_llm_disables_anthropic_retries(monkeypatch):
    class DummyChunk:
        def __init__(self, text: str):
            self.text = text

    class DummyMessage:
        def __init__(self, text: str):
            self.content = [DummyChunk(text)]

    seen = {"with_options": None, "timeout": None}

    class DummyMessages:
        def create(self, *args, **kwargs):
            seen["timeout"] = kwargs.get("timeout")
            return DummyMessage("[]")

    class DummyClient:
        def __init__(self):
            self.messages = DummyMessages()

        def with_options(self, **kwargs):
            seen["with_options"] = kwargs
            return self

    monkeypatch.setattr(ai_analyzer, "client", DummyClient())
    monkeypatch.setattr(ai_analyzer, "ANTHROPIC_DISABLED_REASON", None)
    monkeypatch.setattr(ai_analyzer, "_openai_enabled", lambda: False)

    out = ai_analyzer._extract_obligations_with_llm("[]", timeout_s=12.5)

    assert out == []
    assert seen["with_options"] is not None
    assert seen["with_options"]["max_retries"] == 0
    assert seen["timeout"] == 12.5
