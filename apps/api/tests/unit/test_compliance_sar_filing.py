import pytest
from datetime import datetime, timezone

from src.compliance.sar_filing import SARFilingSystem, UARFilingSystem
from src.models.transaction_models import Transaction, Alert, Case
from src.models.models import LegalDocument


@pytest.mark.unit
def test_sar_prepare_and_file(db_session, monkeypatch):
    tx = Transaction(
        tenant_id="default",
        transaction_id="tx_sar",
        user_id="user_sar",
        amount=100,
        currency="USD",
        transaction_type="deposit",
        timestamp=datetime.now(timezone.utc),
        status="completed",
        country_code="US",
    )
    alert = Alert(
        tenant_id="default",
        alert_id="alert_sar",
        alert_type="velocity",
        severity="high",
        transaction=tx,
        user_id="user_sar",
        status="pending",
        risk_score=90,
    )
    doc = LegalDocument(
        celex="32020R0001",
        title="Test Regulation",
        jurisdiction="EU",
        source_system="eur-lex",
        publication_date=datetime.now(timezone.utc),
    )

    db_session.add_all([tx, alert, doc])
    db_session.commit()

    case = Case(
        tenant_id="default",
        case_id="case_sar",
        subject_type="user",
        subject_id="user_sar",
        summary="Suspicious activity",
        related_alert_ids=[alert.id],
        related_transaction_ids=[tx.id],
        applicable_regulation_ids=[doc.id],
    )
    db_session.add(case)
    db_session.commit()

    system = SARFilingSystem(db_session)
    monkeypatch.setattr(system.enrichment_service, "generate_sar_draft", lambda *args, **kwargs: {"narrative": "AI narrative"})

    sar = system.prepare_sar(case.case_id)
    assert sar["case_reference"] == "case_sar"
    assert sar["suspicious_activity"]["alert_count"] == 1

    dry_run = system.file_sar(sar, jurisdiction="US", dry_run=True)
    assert dry_run["status"] == "dry_run"

    filed = system.file_sar(sar, jurisdiction="US", dry_run=False)
    assert filed["status"] == "filed"
    assert filed["jurisdiction"] == "US_FinCEN"


@pytest.mark.unit
def test_sar_validation_failure(db_session):
    system = SARFilingSystem(db_session)
    with pytest.raises(ValueError):
        system.file_sar({"sar_id": "missing"}, dry_run=True)


@pytest.mark.unit
def test_uar_prepare_and_file(db_session):
    tx = Transaction(
        tenant_id="default",
        transaction_id="tx_uar",
        user_id="user_uar",
        amount=55,
        currency="USD",
        transaction_type="withdrawal",
        timestamp=datetime.now(timezone.utc),
        status="completed",
        country_code="US",
    )
    alert = Alert(
        tenant_id="default",
        alert_id="alert_uar",
        alert_type="unusual",
        severity="medium",
        transaction=tx,
        user_id="user_uar",
        status="pending",
        risk_score=40,
    )
    db_session.add_all([tx, alert])
    db_session.commit()

    system = UARFilingSystem(db_session)
    uar = system.prepare_uar(alert.id)
    assert uar["alert_reference"] == "alert_uar"

    filed = system.file_uar(uar, jurisdiction="EU")
    assert filed["status"] == "filed"
    assert filed["jurisdiction"] == "EU"
