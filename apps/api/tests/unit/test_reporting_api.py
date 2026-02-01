import pytest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from src.api import reporting as reporting_api
from src.auth.dependencies import CurrentUser
from src.models.transaction_models import Transaction, Alert, Case, MonitoringRule, UserRiskProfile
from src.models.models import LegalDocument
from src.models.compliance_workflow import (
    RegulatoryObligation,
    PolicyDocument,
    PolicySection,
    InternalRule,
    OfficialJournalAct,
    RegulatorySource,
)
from src.audit.models import AuditLog, EventRecord, DecisionRecord
from src.models.travel_rule import TravelRuleRequestRecord


@pytest.mark.unit
def test_reporting_endpoints_cover_dashboard_and_exports(db_session, monkeypatch):
    # Stub external systems
    class DummySAR:
        def __init__(self, db):
            self.db = db

        def prepare_sar(self, case_id):
            return {"case_id": case_id, "prepared": True}

        def file_sar(self, sar, jurisdiction, dry_run):
            return {"filing_reference": f"REF-{sar['case_id']}", "dry_run": dry_run}

    class DummyUAR:
        def __init__(self, db):
            self.db = db

        def prepare_uar(self, alert_id):
            return {"alert_id": alert_id, "prepared": True}

    monkeypatch.setattr(reporting_api, "SARFilingSystem", DummySAR)
    monkeypatch.setattr(reporting_api, "UARFilingSystem", DummyUAR)
    monkeypatch.setattr(reporting_api, "publish_event_safe", lambda *args, **kwargs: None)

    now = datetime.now(timezone.utc)
    doc = LegalDocument(
        celex="32023R1234",
        title="Payment service regulation",
        jurisdiction="EU",
        source_system="eur-lex",
        publication_date=now - timedelta(days=10),
        last_modified=now - timedelta(days=2),
        compliance_domain="aml",
        risk_level="high",
        scope_tags=["psp"],
    )
    db_session.add(doc)
    db_session.commit()

    rule = MonitoringRule(
        tenant_id="default",
        rule_id="RULE-1",
        name="High Amount",
        description="Test rule",
        category="velocity",
        severity="high",
        conditions={"conditions": [{"field": "amount", "operator": ">", "value": 1000}], "logic": "AND"},
        thresholds={"transaction_count": 1},
        regulatory_source_id=doc.id,
    )

    txn = Transaction(
        tenant_id="default",
        transaction_id="txn_001",
        user_id="user_1",
        amount=1500.00,
        currency="USD",
        transaction_type="deposit",
        timestamp=now - timedelta(days=1),
        status="completed",
        country_code="US",
        risk_score=70,
        risk_level="high",
    )

    alert = Alert(
        tenant_id="default",
        alert_id="alert_001",
        alert_type="velocity",
        severity="critical",
        transaction=txn,
        user_id="user_1",
        status="pending",
        priority=1,
        description="Velocity spike",
        risk_score=85,
        related_regulations=[doc.id],
        resolution_status="false_positive",
        resolved_at=now - timedelta(hours=1),
    )

    case = Case(
        tenant_id="default",
        case_id="case_001",
        status="closed",
        opened_at=now - timedelta(days=2),
        closed_at=now - timedelta(days=1),
        outcome="sar_filed",
        outcome_notes="Filed",
        related_alert_ids=[],
        related_transaction_ids=[],
    )

    db_session.add_all([rule, txn, alert, case])
    db_session.commit()

    case.related_alert_ids = [alert.id]
    case.related_transaction_ids = [txn.id]
    db_session.commit()

    # Events & decisions for evidence exports
    event_case = EventRecord(
        event_id="evt_case",
        event_type="case.updated",
        entity_type="case",
        entity_id=case.case_id,
    )
    event_alert = EventRecord(
        event_id="evt_alert",
        event_type="alert.created",
        entity_type="alert",
        entity_id=alert.alert_id,
    )
    event_txn = EventRecord(
        event_id="evt_txn",
        event_type="rule.triggered",
        entity_type="transaction",
        entity_id=txn.transaction_id,
    )
    decision = DecisionRecord(
        decision_id="dec_001",
        event_id=event_txn.event_id,
        decision="alert",
    )

    audit = AuditLog(
        audit_id="audit_001",
        actor_id="user_1",
        actor_email="user@example.com",
        actor_role="admin",
        action="create",
        method="POST",
        path="/api/alerts",
        entity_type="alert",
        entity_id=alert.alert_id,
        status_code=200,
    )

    travel_record = TravelRuleRequestRecord(
        request_id="tr_001",
        transaction_id=txn.transaction_id,
        amount="1000",
        currency="USD",
        status="pending",
    )

    db_session.add_all([event_case, event_alert, event_txn, decision, audit, travel_record])
    db_session.commit()

    # Compliance home dashboard dependencies
    obligation = RegulatoryObligation(
        obligation_id="obl_001",
        doc_id=doc.id,
        obligation_text="Payment service providers must monitor transactions.",
        status="draft",
        scope_tags=["psp"],
        updated_at=now,
    )
    policy = PolicyDocument(
        policy_id="pol_001",
        name="AML Policy",
        status="draft",
        owner="compliance",
        updated_at=now,
    )
    policy_section = PolicySection(
        policy=policy,
        section_ref="1",
        title="Monitoring",
        content="Monitor transactions",
        status="draft",
        updated_at=now,
    )
    internal_rule = InternalRule(
        internal_rule_id="IR-001",
        obligation=obligation,
        policy_section=policy_section,
        name="Rule mapping",
        status="draft",
        created_at=now,
        updated_at=now,
    )
    oj_act = OfficialJournalAct(
        act_identifier="OJ-L-001",
        publication_date=now.date(),
    )
    source = RegulatorySource(
        source_key="eur-lex-oj-act-by-act",
        name="OJ Ingestion",
        jurisdiction="EU",
        language="en",
        source_type="rss",
        last_ingested_at=now - timedelta(days=1),
    )
    risk_profile = UserRiskProfile(
        tenant_id="default",
        user_id="user_1",
        risk_level="high",
    )

    db_session.add_all([obligation, policy, policy_section, internal_rule, oj_act, source, risk_profile])
    db_session.commit()

    # SAR / UAR flows
    sar = reporting_api.prepare_sar(case.case_id, db_session, CurrentUser("1", "admin@example.com", "admin"))
    assert sar["case_id"] == case.case_id

    result = reporting_api.file_sar(
        case.case_id,
        "EU",
        False,
        db_session,
        CurrentUser("1", "admin@example.com", "admin"),
    )
    assert "filing_reference" in result

    uar = reporting_api.prepare_uar(alert.id, db_session, CurrentUser("1", "admin@example.com", "admin"))
    assert uar["alert_id"] == alert.id

    # Evidence exports
    case_export = reporting_api.export_case_evidence(case.case_id, db_session, None)
    assert case_export["case"]["case_id"] == case.case_id

    decision_export = reporting_api.export_decision_evidence(decision.decision_id, db_session, None)
    assert decision_export["decision"]["decision_id"] == decision.decision_id

    travel_export = reporting_api.export_travel_rule_evidence(travel_record.request_id, db_session, None)
    assert travel_export["travel_rule_request"]["request_id"] == travel_record.request_id

    # Dashboard + summary reports
    reporting_api.get_compliance_dashboard(None, None, db_session)

    home = reporting_api.compliance_home_dashboard(
        intake_days=7,
        intake_jurisdiction=None,
        intake_source=None,
        intake_limit=5,
        obligation_status="draft",
        obligation_limit=5,
        scope="psp",
        db=db_session,
        _=None,
    )
    assert home["coverage"]["total_documents"] >= 1

    aml_scope = reporting_api.aml_scope_review(
        jurisdiction="EU",
        scope="psp",
        limit=10,
        db=db_session,
        _=None,
    )
    assert aml_scope["total_obligations"] >= 1

    alerts_summary = reporting_api.get_alerts_summary_report(None, None, db_session)
    assert alerts_summary["total_alerts"] >= 1

    tx_summary = reporting_api.get_transactions_summary_report(None, None, db_session)
    assert tx_summary["total_transactions"] >= 1

    coverage = reporting_api.get_regulatory_coverage_report(db_session)
    assert coverage["total_regulations_monitored"] >= 1

    alert_audit = reporting_api.get_alert_audit_trail(alert.alert_id, None, 100, db_session)
    assert alert_audit["count"] >= 1

    case_audit = reporting_api.get_case_audit_trail(case.case_id, None, 100, db_session)
    assert case_audit["count"] >= 1


@pytest.mark.unit
def test_reporting_scope_filters_no_scopes(db_session):
    doc = LegalDocument(
        celex="32023R9999",
        title="Misc regulation",
        jurisdiction="EU",
    )
    db_session.add(doc)
    db_session.commit()

    query = db_session.query(LegalDocument)
    # Empty scope list should no-op
    filtered = reporting_api._apply_scope_filter_to_docs(query, [], db_session)
    assert filtered.count() >= 1

    obligations_query = db_session.query(RegulatoryObligation, LegalDocument).join(
        LegalDocument, RegulatoryObligation.doc_id == LegalDocument.id
    )
    filtered_obl = reporting_api._apply_scope_filter_to_obligations(obligations_query, [], db_session)
    # Query should still be usable even with no obligations
    filtered_obl.count()
