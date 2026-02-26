import pytest
from datetime import datetime, timezone

from src.ingestion.processor import IngestionProcessor
import src.ingestion.processor as processor_module
from src import models


class DummyCellar:
    def query_by_celex(self, celex):
        return {
            "title": "Cellar Title",
            "date_document": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "eli": "eli",
            "cellar_id": "cellar",
            "work_type": "regulation",
        }

    def get_related_documents(self, cellar_id):
        return []


class DummyExtractor:
    def extract_content(self, celex, language="en"):
        return {
            "full_text": "Full text",
            "article_breakdown": [],
            "extraction_method": "html",
            "word_count": 2,
        }


class DummyRAGIndexer:
    def __init__(self, db):
        self.db = db

    def index_document(self, doc):
        return None


@pytest.mark.unit
def test_ingestion_processor_new_and_existing(monkeypatch, db_session):
    processor = IngestionProcessor(db_session)

    monkeypatch.setattr(processor, "cellar", DummyCellar())
    monkeypatch.setattr(processor, "content_extractor", DummyExtractor())
    monkeypatch.setattr("src.ingestion.processor.index_document", lambda doc: True)
    monkeypatch.setattr(
        "src.ingestion.processor.analyze_document",
        lambda data: {
            "compliance_domain": "aml",
            "risk_level": "high",
            "obligations_json": [],
            "implementation_deadline": None,
            "ai_summary": "summary",
            "analyzed_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        },
    )
    monkeypatch.setattr(
        "src.ingestion.processor.seed_obligations_for_doc", lambda *args, **kwargs: None
    )
    monkeypatch.setattr("src.ingestion.processor.RAGIndexer", DummyRAGIndexer)
    monkeypatch.setattr(
        "src.ingestion.processor.settings",
        type(
            "S",
            (),
            {
                "RAG_INDEX_ENABLED": False,
                "REGULATORY_SCOPE_FILTER": "",
            },
        )(),
    )

    entry = {
        "celex": "32016R0679",
        "title": "Test Regulation",
        "published": datetime(2024, 1, 1, tzinfo=timezone.utc).isoformat(),
        "source_system": "eur-lex",
        "source_reference": "ref",
        "link": "http://example.com",
        "language": "en",
        "jurisdiction": "EU",
    }

    result = processor.process_entry(entry)
    assert result == "new"

    # Existing doc path
    entry_update = dict(entry)
    entry_update["title"] = "Updated Title"
    result = processor.process_entry(entry_update)
    assert result in {"updated", "unchanged"}

    # Parse date helper
    assert processor._parse_date("2024-01-01T00:00:00") is not None
    assert processor._parse_date((2024, 1, 1, 0, 0, 0)) is not None


@pytest.mark.unit
def test_ingestion_processor_scope_filter_invalid_config_fails_closed(monkeypatch, db_session):
    processor = IngestionProcessor(db_session)
    monkeypatch.setattr(processor_module.settings, "REGULATORY_SCOPE_FILTER", "aml,kyc")

    assert (
        processor._matches_scope(
            "Payment services compliance update",
            {"description": "PSD2 requirements for PSPs"},
        )
        is False
    )


@pytest.mark.unit
def test_ingestion_processor_scope_filter_accepts_psan_alias(monkeypatch, db_session):
    processor = IngestionProcessor(db_session)
    monkeypatch.setattr(processor_module.settings, "REGULATORY_SCOPE_FILTER", "psan")

    assert (
        processor._matches_scope(
            "Markets in Crypto-Assets regulation",
            {"description": "Obligations for crypto-asset service providers", "topics": ["MiCA"]},
        )
        is True
    )
    assert processor._matches_scope("Public procurement notice", {"description": "roads"}) is False
