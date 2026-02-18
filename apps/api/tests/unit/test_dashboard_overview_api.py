from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from src.api import dashboard_overview as overview_api
from src.api import monitoring_dashboard as monitoring_api
from src.config import settings
from src.models.transaction_models import Alert, Case, Transaction


@pytest.mark.unit
def test_dashboard_overview_returns_expected_contract(db_session):
    now = datetime.now(timezone.utc)
    txn = Transaction(
        tenant_id="default",
        transaction_id="txn_dashboard_overview",
        user_id="user_dashboard",
        amount=1450,
        currency="EUR",
        transaction_type="transfer",
        timestamp=now - timedelta(hours=2),
        status="flagged",
        risk_level="high",
        risk_score=77,
    )
    alert = Alert(
        tenant_id="default",
        alert_id="alert_dashboard_overview",
        alert_type="velocity",
        severity="critical",
        transaction=txn,
        user_id="user_dashboard",
        status="pending",
        priority=1,
        risk_score=88,
        created_at=now - timedelta(hours=1),
    )
    case = Case(
        tenant_id="default",
        case_id="case_dashboard_overview",
        status="open",
        priority="high",
        opened_at=now - timedelta(hours=3),
    )

    db_session.add_all([txn, alert, case])
    db_session.commit()

    payload = overview_api.get_dashboard_overview(
        view="operations",
        time_range="7d",
        limit=12,
        db=db_session,
        _=None,
    )

    assert payload["view"] == "operations"
    assert payload["time_range"] == "7d"
    assert "kpis" in payload
    assert "system_health" in payload
    assert "queues" in payload
    assert "critical_bar" in payload
    assert "queue_summary" in payload
    assert "governance" in payload
    assert "throughput" in payload
    assert isinstance(payload["queues"]["alerts"], list)
    assert isinstance(payload["queues"]["cases"], list)
    assert payload["kpis"]["pending_alerts"] >= 1
    assert isinstance(payload["critical_bar"]["p1_sla_breaches"], int)
    assert isinstance(payload["governance"]["alert_to_case_rate"], float)


@pytest.mark.unit
def test_dashboard_overview_respects_feature_flag(db_session):
    previous = settings.DASHBOARD_V2_ENABLED
    settings.DASHBOARD_V2_ENABLED = False
    try:
        with pytest.raises(HTTPException) as exc_info:
            overview_api.get_dashboard_overview(
                view="operations",
                time_range="7d",
                limit=12,
                db=db_session,
                _=None,
            )
        assert exc_info.value.status_code == 503
    finally:
        settings.DASHBOARD_V2_ENABLED = previous


@pytest.mark.unit
def test_monitoring_metrics_alias_matches_realtime_payload(db_session):
    realtime = monitoring_api.get_realtime_metrics(db_session)
    compat = monitoring_api.get_realtime_metrics_compat(db_session)

    keys_to_compare = [
        "transactions_last_hour",
        "alerts_last_hour",
        "critical_alerts_pending",
        "high_risk_transactions_last_hour",
        "average_processing_time_ms",
        "system_status",
    ]

    for key in keys_to_compare:
        assert realtime[key] == compat[key]
