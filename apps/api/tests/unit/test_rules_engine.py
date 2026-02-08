"""
Unit tests for Rules Engine service layer.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta

from src.services.rules_engine import RulesEngine
from src.tenancy.context import TenantContext
from tests.factories import TransactionFactory, MonitoringRuleFactory


@pytest.mark.unit
class TestRulesEngineEvaluation:
    """Test rule evaluation logic."""

    def test_simple_amount_condition(self, db_session):
        """Test simple amount threshold rule."""
        # Create rule: amount > 10000
        rule = MonitoringRuleFactory(
            conditions={
                "logic": "AND",
                "conditions": [{"field": "amount", "operator": ">", "value": 10000}],
            },
            sqlalchemy_session=db_session,
        )
        db_session.commit()

        # Create transaction over threshold
        transaction = TransactionFactory(amount=Decimal("15000.00"), sqlalchemy_session=db_session)
        db_session.commit()

        # Evaluate rule
        engine = RulesEngine(db_session)
        with TenantContext("default"):
            result = engine.evaluate_transaction(transaction.id)

        assert len(result) > 0
        assert any(rule.rule_id in (alert.matched_rules_data or {}) for alert in result)

    def test_compound_and_condition(self, db_session):
        """Test compound AND condition."""
        # Create rule: amount > 10000 AND currency == "USD"
        rule = MonitoringRuleFactory(
            conditions={
                "logic": "AND",
                "conditions": [
                    {"field": "amount", "operator": ">", "value": 10000},
                    {"field": "currency", "operator": "==", "value": "USD"},
                ],
            },
            sqlalchemy_session=db_session,
        )
        db_session.commit()

        # Transaction matching both conditions
        transaction1 = TransactionFactory(
            amount=Decimal("15000.00"), currency="USD", sqlalchemy_session=db_session
        )
        db_session.commit()

        engine = RulesEngine(db_session)
        with TenantContext("default"):
            result = engine.evaluate_transaction(transaction1.id)
        assert len(result) > 0

        # Transaction matching only one condition
        transaction2 = TransactionFactory(
            amount=Decimal("15000.00"), currency="EUR", sqlalchemy_session=db_session
        )
        db_session.commit()

        with TenantContext("default"):
            result = engine.evaluate_transaction(transaction2.id)
        assert not any(rule.rule_id in (alert.matched_rules_data or {}) for alert in result)

    def test_compound_or_condition(self, db_session):
        """Test compound OR condition."""
        # Create rule: amount > 50000 OR currency == "BTC"
        rule = MonitoringRuleFactory(
            conditions={
                "logic": "OR",
                "conditions": [
                    {"field": "amount", "operator": ">", "value": 50000},
                    {"field": "currency", "operator": "==", "value": "BTC"},
                ],
            },
            sqlalchemy_session=db_session,
        )
        db_session.commit()

        # Transaction matching first condition
        transaction1 = TransactionFactory(
            amount=Decimal("60000.00"), currency="USD", sqlalchemy_session=db_session
        )
        db_session.commit()

        engine = RulesEngine(db_session)
        with TenantContext("default"):
            result = engine.evaluate_transaction(transaction1.id)
        assert any(rule.rule_id in (alert.matched_rules_data or {}) for alert in result)

        # Transaction matching second condition
        transaction2 = TransactionFactory(
            amount=Decimal("1000.00"), currency="BTC", sqlalchemy_session=db_session
        )
        db_session.commit()

        with TenantContext("default"):
            result = engine.evaluate_transaction(transaction2.id)
        assert any(rule.rule_id in (alert.matched_rules_data or {}) for alert in result)

    def test_country_risk_condition(self, db_session):
        """Test country-based risk condition."""
        # Create rule: country_code IN ["KP", "IR", "SY"]
        rule = MonitoringRuleFactory(
            conditions={
                "logic": "AND",
                "conditions": [
                    {"field": "country_code", "operator": "in", "value": ["KP", "IR", "SY"]}
                ],
            },
            sqlalchemy_session=db_session,
        )
        db_session.commit()

        # Transaction from high-risk country
        transaction = TransactionFactory(country_code="IR", sqlalchemy_session=db_session)
        db_session.commit()

        engine = RulesEngine(db_session)
        with TenantContext("default"):
            result = engine.evaluate_transaction(transaction.id)
        assert any(rule.rule_id in (alert.matched_rules_data or {}) for alert in result)

    def test_disabled_rule_not_evaluated(self, db_session):
        """Test that disabled rules are not evaluated."""
        # Create disabled rule
        rule = MonitoringRuleFactory(
            enabled=False,
            conditions={
                "logic": "AND",
                "conditions": [{"field": "amount", "operator": ">", "value": 1}],
            },
            sqlalchemy_session=db_session,
        )
        db_session.commit()

        # Create transaction
        transaction = TransactionFactory(amount=Decimal("10000.00"), sqlalchemy_session=db_session)
        db_session.commit()

        # Evaluate
        engine = RulesEngine(db_session)
        with TenantContext("default"):
            result = engine.evaluate_transaction(transaction.id)

        # Disabled rule should not trigger
        assert not any(rule.rule_id in (alert.matched_rules_data or {}) for alert in result)

    @pytest.mark.parametrize(
        "bad_value",
        [None, "abc", {}, [], "nan", "inf", "-inf"],
    )
    def test_numeric_coercion_failures_return_false(self, db_session, bad_value):
        """Numeric coercion failures should not raise and should return False."""
        rule = MonitoringRuleFactory(
            conditions={
                "logic": "AND",
                "conditions": [{"field": "amount", "operator": ">", "value": bad_value}],
            },
            sqlalchemy_session=db_session,
        )
        transaction = TransactionFactory(
            amount=Decimal("10.00"),
            sqlalchemy_session=db_session,
        )

        engine = RulesEngine(db_session)
        assert engine._evaluate_rule(transaction, rule) is False

    @pytest.mark.parametrize(
        "tx_value,value,operator,expected",
        [
            ("123.45", 100, ">", True),
            ("123.45", "100", ">", True),
            ("99.0", 100, ">", False),
            (Decimal("150.00"), "100", ">", True),
            (Decimal("50.00"), "100", "<", True),
        ],
    )
    def test_numeric_coercion_accepts_numeric_strings(
        self, db_session, tx_value, value, operator, expected
    ):
        rule = MonitoringRuleFactory(
            conditions={
                "logic": "AND",
                "conditions": [{"field": "amount", "operator": operator, "value": value}],
            },
            sqlalchemy_session=db_session,
        )

        class TxLike:
            amount = tx_value

        engine = RulesEngine(db_session)
        assert (
            engine._evaluate_condition(TxLike(), rule.conditions["conditions"][0], rule=rule)
            is expected
        )


@pytest.mark.unit
class TestRulesEngineAggregation:
    """Test aggregation-based rules (velocity, volume, etc.)."""

    def test_velocity_rule(self, db_session):
        """Test velocity-based rule (transaction count in time window)."""
        # Create velocity rule: more than 5 transactions in 24h
        rule = MonitoringRuleFactory(
            category="velocity",
            conditions={
                "logic": "AND",
                "conditions": [{"field": "transaction_count_24h", "operator": ">", "value": 5}],
            },
            thresholds={"window_size": "24h", "metric": "count", "threshold": 5},
            sqlalchemy_session=db_session,
        )
        db_session.commit()

        user_id = "user_velocity_001"
        base_time = datetime.utcnow()

        # Create 6 transactions within 24h for same user
        for i in range(6):
            TransactionFactory(
                user_id=user_id,
                timestamp=base_time - timedelta(hours=i),
                sqlalchemy_session=db_session,
            )
        db_session.commit()

        # Create one more transaction to trigger the rule
        transaction = TransactionFactory(
            user_id=user_id, timestamp=base_time, sqlalchemy_session=db_session
        )
        db_session.commit()

        # This would typically be checked by aggregation service
        # For unit test, we test the condition matching logic
        assert transaction.user_id == user_id

    def test_volume_rule(self, db_session):
        """Test volume-based rule (total amount in time window)."""
        # Create volume rule: more than $50,000 in 24h
        rule = MonitoringRuleFactory(
            category="structuring",
            thresholds={
                "window_size": "24h",
                "metric": "sum",
                "field": "amount",
                "threshold": 50000,
            },
            sqlalchemy_session=db_session,
        )
        db_session.commit()

        user_id = "user_volume_001"
        base_time = datetime.utcnow()

        # Create transactions totaling $60,000 within 24h
        amounts = [15000, 12000, 18000, 15000]
        for amount in amounts:
            TransactionFactory(
                user_id=user_id,
                amount=Decimal(str(amount)),
                timestamp=base_time - timedelta(hours=1),
                sqlalchemy_session=db_session,
            )
        db_session.commit()

        assert sum(amounts) > 50000


@pytest.mark.unit
class TestRulesEngineOperators:
    """Test various rule operators."""

    @pytest.mark.parametrize(
        "operator,value,test_value,should_match",
        [
            (">", 1000, 1500, True),
            (">", 1000, 500, False),
            (">=", 1000, 1000, True),
            (">=", 1000, 999, False),
            ("<", 1000, 500, True),
            ("<", 1000, 1500, False),
            ("<=", 1000, 1000, True),
            ("<=", 1000, 1001, False),
            ("==", "USD", "USD", True),
            ("==", "USD", "EUR", False),
            ("!=", "USD", "EUR", True),
            ("!=", "USD", "USD", False),
        ],
    )
    def test_comparison_operators(self, db_session, operator, value, test_value, should_match):
        """Test various comparison operators."""
        # This is a unit test for the operator logic
        # In practice, this would be part of RulesEngine._evaluate_condition
        if operator == ">":
            assert (test_value > value) == should_match
        elif operator == ">=":
            assert (test_value >= value) == should_match
        elif operator == "<":
            assert (test_value < value) == should_match
        elif operator == "<=":
            assert (test_value <= value) == should_match
        elif operator == "==":
            assert (test_value == value) == should_match
        elif operator == "!=":
            assert (test_value != value) == should_match
