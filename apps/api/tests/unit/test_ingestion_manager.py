import pytest
from datetime import datetime

from src.ingestion.manager import IngestionManager
import src.ingestion.manager as manager_module
from src.ingestion.alerts import IngestionReport
from src.models.compliance_workflow import RegulatorySource


class DummyProcessor:
    def __init__(self, db):
        self.db = db
        self.calls = []
        self.next_results = ["new", "updated", "skipped", "unchanged"]

    def process_entry(self, entry):
        self.calls.append(entry)
        return self.next_results[min(len(self.calls) - 1, len(self.next_results) - 1)]


@pytest.mark.unit
def test_ingestion_manager_manual_run(db_session, monkeypatch):
    monkeypatch.setattr(manager_module.settings, "EURLEX_LANGUAGES", "en")
    monkeypatch.setattr(manager_module.settings, "LEGIFRANCE_JORF_RSS_URL", None)

    entries = [
        {"celex": "32024R0001", "link": "link1"},
        {"celex": "32024R0002", "link": "link2"},
    ]

    manager = IngestionManager(db_session)
    manager.processor = DummyProcessor(db_session)

    monkeypatch.setattr(manager.rss, "get_latest_oj_entries", lambda **kwargs: entries)
    monkeypatch.setattr(manager_module, "send_ingestion_report", lambda reports: True)
    monkeypatch.setattr(manager_module, "send_ingestion_failure_alert", lambda **kwargs: True)

    reports = manager.run_manual_ingestion(source_keys=["eur-lex-oj-en"], send_alerts=False)
    assert reports
    assert reports[0].items_seen == len(entries)


@pytest.mark.unit
def test_ingestion_manager_get_or_create_source(db_session):
    manager = IngestionManager(db_session)
    config = {
        "source_key": "eur-lex-oj-en",
        "name": "EUR-Lex Official Journal (EN)",
        "jurisdiction": "EU",
        "language": "en",
        "source_type": "rss",
        "base_url": "https://eur-lex.europa.eu",
        "schedule": "weekly",
    }

    source = manager._get_or_create_source(config)
    assert source.source_key == "eur-lex-oj-en"

    # Update existing
    config["name"] = "EUR-Lex Updated"
    updated = manager._get_or_create_source(config)
    assert updated.name == "EUR-Lex Updated"


@pytest.mark.unit
def test_process_source_does_not_advance_watermark_on_failed_fetch(db_session, monkeypatch):
    manager = IngestionManager(db_session)
    manager.processor = DummyProcessor(db_session)

    previous_watermark = datetime(2024, 1, 15)
    config = {
        "source_key": "eur-lex-oj-en",
        "name": "EUR-Lex Official Journal (EN)",
        "jurisdiction": "EU",
        "language": "en",
        "source_type": "rss",
        "base_url": "https://eur-lex.europa.eu",
        "schedule": "weekly",
        "fetch": lambda *_: (_ for _ in ()).throw(RuntimeError("fetch failed")),
    }

    source = manager._get_or_create_source(config)
    source.last_ingested_at = previous_watermark
    db_session.commit()

    monkeypatch.setattr(manager_module, "retry_with_backoff", lambda func, **_: func())

    report = manager._process_source(config)
    db_session.refresh(source)

    assert report.status == "failed"
    assert source.last_ingested_at == previous_watermark


@pytest.mark.unit
def test_process_source_advances_watermark_on_success(db_session, monkeypatch):
    manager = IngestionManager(db_session)
    manager.processor = DummyProcessor(db_session)

    previous_watermark = datetime(2024, 1, 15)
    config = {
        "source_key": "eur-lex-oj-en",
        "name": "EUR-Lex Official Journal (EN)",
        "jurisdiction": "EU",
        "language": "en",
        "source_type": "rss",
        "base_url": "https://eur-lex.europa.eu",
        "schedule": "weekly",
        "fetch": lambda *_: [],
    }

    source = manager._get_or_create_source(config)
    source.last_ingested_at = previous_watermark
    db_session.commit()

    monkeypatch.setattr(manager_module, "retry_with_backoff", lambda func, **_: func())

    report = manager._process_source(config)
    db_session.refresh(source)

    assert report.status == "completed"
    assert source.last_ingested_at is not None
    assert source.last_ingested_at > previous_watermark
