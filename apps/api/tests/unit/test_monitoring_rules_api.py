import pytest
from datetime import datetime, timezone
from fastapi import HTTPException

from src.api import monitoring_rules as rules_api
from src.auth.dependencies import CurrentUser
from src.schemas.transaction_schemas import (
    MonitoringRuleCreate,
    RuleVersionCreate,
    RuleSimulationRequest,
    RuleBacktestRequest,
)
from src.models.transaction_models import Transaction, Alert
from src.tenancy.context import set_current_tenant, clear_current_tenant


@pytest.mark.unit
def test_monitoring_rules_crud_and_simulation(db_session):
    set_current_tenant("default")
    try:
        # Invalid rule rejected at creation time
        invalid_rule_payload = MonitoringRuleCreate(
            name="Invalid Rule",
            description="Has an unknown field",
            category="amount_threshold",
            severity="high",
            conditions={
                "conditions": [
                    {"field": "does_not_exist", "operator": ">", "value": 1000},
                ],
                "logic": "AND",
            },
            thresholds=None,
            enabled=True,
        )
        with pytest.raises(HTTPException) as exc:
            rules_api.create_rule(invalid_rule_payload, db_session)
        assert exc.value.status_code == 400
        assert "errors" in (exc.value.detail or {})

        rule_payload = MonitoringRuleCreate(
            name="High Amount",
            description="Detect high amount",
            category="amount_threshold",
            severity="high",
            conditions={
                "conditions": [
                    {"field": "amount", "operator": ">", "value": 1000},
                    {"field": "currency", "operator": "==", "value": "USD"},
                ],
                "logic": "AND",
            },
            thresholds=None,
            enabled=True,
        )
        rule = rules_api.create_rule(rule_payload, db_session)
        assert rule.rule_id

        rules = rules_api.list_rules(0, 100, None, None, None, db_session)
        assert len(rules) >= 1

        fetched = rules_api.get_rule(rule.rule_id, db_session, "default")
        assert fetched.rule_id == rule.rule_id

        with pytest.raises(HTTPException):
            rules_api.update_rule(rule.rule_id, None, db_session)

        disabled = rules_api.disable_rule(rule.rule_id, db_session, "default")
        assert disabled["status"] == "disabled"

        enabled = rules_api.enable_rule(rule.rule_id, db_session, "default")
        assert enabled["status"] == "enabled"

        # Create a transaction for simulation/backtest
        txn = Transaction(
            tenant_id="default",
            transaction_id="txn_rule_1",
            user_id="user_1",
            amount=1500.00,
            currency="USD",
            transaction_type="deposit",
            timestamp=datetime.now(timezone.utc),
            status="completed",
            country_code="US",
        )
        db_session.add(txn)
        db_session.commit()

        test_result = rules_api.test_rule(rule.rule_id, txn.id, db_session, "default")
        assert test_result["would_trigger"] is True

        sim = rules_api.simulate_rule(
            rule.rule_id,
            RuleSimulationRequest(transaction_id=txn.id),
            db_session,
            "default",
        )
        assert sim.would_trigger is True

        backtest = rules_api.backtest_rule(
            rule.rule_id,
            RuleBacktestRequest(limit=10, sample_size=2),
            db_session,
            "default",
        )
        assert backtest.total_transactions >= 1

        # Rule versions
        current_user = CurrentUser("user-1", "user@example.com", "admin")
        version = rules_api.create_rule_version(
            rule.rule_id,
            RuleVersionCreate(description="Update"),
            db_session,
            current_user,
            "default",
        )
        assert version.status == "pending"

        approved = rules_api.approve_rule_version(version.id, db_session, current_user, "default")
        assert approved.status == "approved"

        versions = rules_api.list_rule_versions(rule.rule_id, db_session, "default")
        assert versions

        all_versions = rules_api.list_versions(None, db_session)
        assert all_versions

        # Template rules
        amt_rule = rules_api.create_amount_threshold_rule(
            name="Limit EUR",
            amount_limit=5000,
            currency="EUR",
            severity="medium",
            regulatory_source_id=None,
            db=db_session,
        )
        assert amt_rule.rule_id.startswith("RULE-AMT")

        geo_rule = rules_api.create_high_risk_country_rule(
            name="High Risk Countries",
            country_codes=["IR", "KP"],
            severity="high",
            regulatory_source_id=None,
            db=db_session,
        )
        assert geo_rule.rule_id.startswith("RULE-GEO")

        vel_rule = rules_api.create_velocity_rule(
            name="Velocity Rule",
            max_transactions=10,
            time_window_hours=24,
            severity="medium",
            regulatory_source_id=None,
            db=db_session,
        )
        assert vel_rule.rule_id.startswith("RULE-VEL")

        stats = rules_api.get_rules_statistics(db_session)
        assert stats["total_rules"] >= 1

        top = rules_api.get_top_performing_rules(limit=10, metric="alert_count", db=db_session)
        assert isinstance(top, list)

        bulk_enabled = rules_api.bulk_enable_rules([rule.rule_id], db_session)
        assert bulk_enabled["enabled_count"] >= 1

        bulk_disabled = rules_api.bulk_disable_rules([rule.rule_id], db_session)
        assert bulk_disabled["disabled_count"] >= 1

        bulk_update = rules_api.bulk_update_severity([rule.rule_id], "critical", db_session)
        assert bulk_update["new_severity"] == "critical"

        with pytest.raises(HTTPException):
            rules_api.bulk_update_severity([rule.rule_id], "invalid", db_session)

        deleted = rules_api.delete_rule(rule.rule_id, db_session, "default")
        assert deleted["status"] == "deleted"
    finally:
        clear_current_tenant()
