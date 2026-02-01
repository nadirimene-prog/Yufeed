import pytest
from datetime import datetime, timedelta, timezone

from src.api import monitoring_dashboard as dashboard_api
from src.models.transaction_models import Transaction, Alert, Case, MonitoringRule, UserRiskProfile
from src.models.models import LegalDocument


@pytest.mark.unit
def test_monitoring_dashboard_and_metrics(db_session):
    now = datetime.now(timezone.utc)
    doc = LegalDocument(
        celex="32024R5555",
        title="AML Regulation",
        jurisdiction="EU",
    )
    db_session.add(doc)
    db_session.commit()

    rule = MonitoringRule(
        tenant_id="default",
        rule_id="RULE-555",
        name="High Risk",
        description="High risk rule",
        category="velocity",
        severity="high",
        conditions={"conditions": [{"field": "amount", "operator": ">", "value": 1000}], "logic": "AND"},
        thresholds=None,
        enabled=True,
        alert_count=5,
        regulatory_source_id=doc.id,
    )

    txn1 = Transaction(
        tenant_id="default",
        transaction_id="txn_dash_1",
        user_id="user_1",
        amount=2000,
        currency="USD",
        transaction_type="deposit",
        timestamp=now - timedelta(hours=2),
        status="flagged",
        country_code="US",
        risk_level="high",
    )
    txn2 = Transaction(
        tenant_id="default",
        transaction_id="txn_dash_2",
        user_id="user_2",
        amount=100,
        currency="EUR",
        transaction_type="withdrawal",
        timestamp=now - timedelta(days=1),
        status="blocked",
        country_code="FR",
        risk_level="low",
    )

    alert1 = Alert(
        tenant_id="default",
        alert_id="alert_dash_1",
        alert_type="velocity",
        severity="critical",
        transaction=txn1,
        user_id="user_1",
        status="pending",
        priority=1,
        created_at=now - timedelta(hours=3),
    )
    alert2 = Alert(
        tenant_id="default",
        alert_id="alert_dash_2",
        alert_type="structuring",
        severity="high",
        transaction=txn2,
        user_id="user_2",
        status="resolved",
        priority=3,
        created_at=now - timedelta(days=2),
    )

    case = Case(
        tenant_id="default",
        case_id="case_dash",
        status="open",
        priority="high",
        opened_at=now - timedelta(days=1),
    )

    profile = UserRiskProfile(
        tenant_id="default",
        user_id="user_1",
        overall_risk_score=90,
        risk_level="high",
    )

    db_session.add_all([rule, txn1, txn2, alert1, alert2, case, profile])
    db_session.commit()

    dashboard = dashboard_api.get_monitoring_dashboard(30, db_session)
    assert dashboard.alert_stats.total_alerts >= 1

    realtime = dashboard_api.get_realtime_metrics(db_session)
    assert realtime["transactions_last_hour"] >= 0

    alert_trends = dashboard_api.get_alert_trends(30, db_session)
    assert "trends" in alert_trends

    txn_trends = dashboard_api.get_transaction_trends(30, db_session)
    assert "trends" in txn_trends

    health = dashboard_api.get_system_health(db_session)
    assert health["status"] in {"healthy", "warning", "degraded"}

    coverage = dashboard_api.get_compliance_coverage(db_session)
    assert coverage["total_rules"] >= 1
