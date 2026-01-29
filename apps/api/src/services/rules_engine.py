"""
Rules Engine Service
Evaluates transactions against monitoring rules and generates alerts.

This is Yufeed's innovation: rules are linked to specific EU regulations,
providing regulatory context for every alert.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid
import logging


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)

from src.models.transaction_models import (
    Transaction, Alert, MonitoringRule, UserRiskProfile
)
from src.models.models import LegalDocument
from src.audit.recorders import record_event, record_decision

logger = logging.getLogger(__name__)


class RulesEngine:
    """
    Evaluates transactions against monitoring rules.

    Rule DSL Structure:
    {
        "conditions": [
            {
                "field": "amount",
                "operator": "greater_than",
                "value": 10000
            },
            {
                "field": "country_code",
                "operator": "in",
                "value": ["IR", "KP", "SY"]
            }
        ],
        "logic": "AND"  # or "OR"
    }
    """

    def __init__(self, db: Session):
        self.db = db

    def evaluate_transaction(self, transaction_id: int) -> List[Alert]:
        """
        Evaluate a transaction against all enabled rules.

        Returns list of alerts generated.
        """
        transaction = self.db.query(Transaction).filter(
            Transaction.id == transaction_id
        ).first()

        if not transaction:
            logger.error(f"Transaction {transaction_id} not found")
            return []

        # Get all enabled rules
        rules = self.db.query(MonitoringRule).filter(
            MonitoringRule.enabled == True
        ).all()

        alerts = []

        for rule in rules:
            if self._evaluate_rule(transaction, rule):
                alert = self._create_alert(transaction, rule)
                alerts.append(alert)

                # Update rule metrics
                rule.alert_count += 1

        self.db.commit()

        return alerts

    def _evaluate_rule(self, transaction: Transaction, rule: MonitoringRule) -> bool:
        """
        Evaluate a single rule against a transaction.
        """
        try:
            conditions = rule.conditions.get("conditions", [])
            logic = rule.conditions.get("logic", "AND")

            if not conditions:
                return False

            results = []
            for condition in conditions:
                result = self._evaluate_condition(transaction, condition)
                results.append(result)

            # Apply logic
            if logic == "AND":
                return all(results)
            elif logic == "OR":
                return any(results)
            else:
                logger.warning(f"Unknown logic operator: {logic}")
                return False

        except Exception as e:
            logger.error(f"Error evaluating rule {rule.rule_id}: {e}")
            return False

    def _evaluate_condition(self, transaction: Transaction, condition: Dict[str, Any]) -> bool:
        """
        Evaluate a single condition.
        """
        field = condition.get("field")
        operator = condition.get("operator")
        value = condition.get("value")

        if not all([field, operator]):
            return False

        operator_aliases = {
            "==": "equals",
            "=": "equals",
            "!=": "not_equals",
            ">": "greater_than",
            ">=": "greater_than_or_equal",
            "<": "less_than",
            "<=": "less_than_or_equal",
        }
        operator = operator_aliases.get(operator, operator)

        # Get transaction field value
        tx_value = getattr(transaction, field, None)

        if tx_value is None:
            return False

        # Evaluate based on operator
        if operator == "equals":
            return tx_value == value

        elif operator == "not_equals":
            return tx_value != value

        elif operator == "greater_than":
            return float(tx_value) > float(value)

        elif operator == "less_than":
            return float(tx_value) < float(value)

        elif operator == "greater_than_or_equal":
            return float(tx_value) >= float(value)

        elif operator == "less_than_or_equal":
            return float(tx_value) <= float(value)

        elif operator == "in":
            return tx_value in value

        elif operator == "not_in":
            return tx_value not in value

        elif operator == "contains":
            return value in str(tx_value)

        elif operator == "starts_with":
            return str(tx_value).startswith(str(value))

        elif operator == "ends_with":
            return str(tx_value).endswith(str(value))

        else:
            logger.warning(f"Unknown operator: {operator}")
            return False

    def _build_transaction_like(self, payload: Dict[str, Any]):
        """
        Build a lightweight transaction-like object for simulation.
        """
        class TransactionLike:
            pass

        tx = TransactionLike()
        for key, value in payload.items():
            setattr(tx, key, value)
        return tx

    def evaluate_rule_details(self, transaction: Transaction, rule: MonitoringRule):
        """
        Evaluate a rule and return condition-level results.
        """
        conditions = rule.conditions.get("conditions", []) if rule.conditions else []
        logic = rule.conditions.get("logic", "AND") if rule.conditions else "AND"

        results = []
        for condition in conditions:
            results.append({
                "condition": condition,
                "passed": self._evaluate_condition(transaction, condition)
            })

        if not conditions:
            return False, results, logic

        if logic == "AND":
            would_trigger = all(item["passed"] for item in results)
        elif logic == "OR":
            would_trigger = any(item["passed"] for item in results)
        else:
            logger.warning(f"Unknown logic operator: {logic}")
            would_trigger = False

        return would_trigger, results, logic

    def simulate_rule(self, rule: MonitoringRule, payload: Dict[str, Any]):
        """
        Evaluate a rule against a payload without writing alerts.
        """
        transaction_like = self._build_transaction_like(payload)
        return self.evaluate_rule_details(transaction_like, rule)

    def _create_alert(self, transaction: Transaction, rule: MonitoringRule) -> Alert:
        """
        Create an alert when a rule is triggered.

        YUFEED INNOVATION: Automatically adds regulatory context.
        """
        # Generate alert ID
        alert_id = f"ALT-{utc_now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

        # Build evidence
        evidence = {
            "rule_id": rule.rule_id,
            "rule_name": rule.name,
            "transaction_id": transaction.transaction_id,
            "transaction_amount": float(transaction.amount),
            "transaction_type": transaction.transaction_type,
            "country_code": transaction.country_code,
            "triggered_at": utc_now().isoformat()
        }

        # Get regulatory context
        regulation_context = None
        related_regulations = []

        if rule.regulatory_source_id:
            legal_doc = self.db.query(LegalDocument).filter(
                LegalDocument.id == rule.regulatory_source_id
            ).first()

            if legal_doc:
                related_regulations = [legal_doc.id]
                regulation_context = self._generate_regulatory_context(
                    transaction, rule, legal_doc
                )

        # Create alert
        alert = Alert(
            tenant_id=transaction.tenant_id,
            alert_id=alert_id,
            alert_type=rule.category or 'compliance_violation',
            severity=rule.severity,
            transaction_id=transaction.id,
            user_id=transaction.user_id,
            status='pending',
            priority=self._calculate_priority(rule.severity),
            description=f"Rule triggered: {rule.name}",
            risk_score=transaction.risk_score,
            matched_rules_data={rule.rule_id: rule.name},
            evidence=evidence,
            related_regulations=related_regulations,
            regulation_context=regulation_context
        )

        self.db.add(alert)

        event_record = record_event(
            self.db,
            event_type="rule.triggered",
            entity_type="transaction",
            entity_id=transaction.transaction_id,
            payload={
                "rule_id": rule.rule_id,
                "rule_name": rule.name,
                "severity": rule.severity,
                "transaction_id": transaction.transaction_id,
            },
            metadata={"rule_version": rule.version},
        )
        record_decision(
            self.db,
            decision="alert",
            event_id=event_record.event_id,
            reason_codes=[rule.rule_id],
            rule_version=str(rule.version) if rule.version is not None else None,
            evidence=evidence,
            metadata={"rule_name": rule.name, "severity": rule.severity},
        )

        # Update transaction status
        if rule.severity in ['critical', 'high']:
            transaction.status = 'flagged'

        logger.info(f"Alert {alert_id} created for transaction {transaction.transaction_id}")

        return alert

    def _generate_regulatory_context(
        self,
        transaction: Transaction,
        rule: MonitoringRule,
        legal_doc: LegalDocument
    ) -> str:
        """
        Generate AI-powered regulatory context explanation.

        YUFEED INNOVATION: Links transaction patterns to specific regulations.
        """
        context = f"""
This alert is linked to {legal_doc.celex} - {legal_doc.title}.

Rule: {rule.name}
Regulatory Basis: {rule.regulatory_requirement or 'Compliance monitoring'}

The transaction triggered this rule due to:
- Amount: {transaction.amount} {transaction.currency}
- Type: {transaction.transaction_type}
- Country: {transaction.country_code}
- Risk Score: {transaction.risk_score}

Regulatory Requirement:
{legal_doc.summary if hasattr(legal_doc, 'summary') else 'See full regulation for details'}

Article Reference: {rule.regulation_article or 'General compliance'}
"""

        # TODO: Use Claude API to generate more sophisticated context
        # This would analyze the transaction pattern against the actual regulation text

        return context.strip()

    def _calculate_priority(self, severity: str) -> int:
        """
        Calculate alert priority based on severity.

        Returns 1 (highest) to 5 (lowest).
        """
        severity_map = {
            'critical': 1,
            'high': 2,
            'medium': 3,
            'low': 4
        }
        return severity_map.get(severity, 3)

    def evaluate_velocity_rules(self, user_id: str) -> List[Alert]:
        """
        Evaluate velocity-based rules for a user.

        Velocity rules check transaction patterns over time:
        - Number of transactions in time window
        - Total amount in time window
        - Unusual patterns compared to user's baseline
        """
        # Get user's recent transactions
        start_time = utc_now() - timedelta(hours=24)

        transactions = self.db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.timestamp >= start_time
        ).order_by(Transaction.timestamp.desc()).all()

        if not transactions:
            return []

        # Get velocity rules
        velocity_rules = self.db.query(MonitoringRule).filter(
            MonitoringRule.enabled == True,
            MonitoringRule.category == 'velocity'
        ).all()

        alerts = []

        for rule in velocity_rules:
            if self._evaluate_velocity_rule(transactions, rule, user_id):
                alert = self._create_velocity_alert(transactions, rule, user_id)
                alerts.append(alert)
                rule.alert_count += 1

        self.db.commit()

        return alerts

    def _evaluate_velocity_rule(
        self,
        transactions: List[Transaction],
        rule: MonitoringRule,
        user_id: str
    ) -> bool:
        """
        Evaluate a velocity rule against a set of transactions.
        """
        thresholds = rule.thresholds or {}

        # Transaction count threshold
        if "transaction_count" in thresholds:
            max_count = thresholds["transaction_count"]
            time_window_hours = thresholds.get("time_window_hours", 24)

            cutoff_time = utc_now() - timedelta(hours=time_window_hours)
            recent_count = sum(1 for tx in transactions if tx.timestamp >= cutoff_time)

            if recent_count > max_count:
                return True

        # Total amount threshold
        if "total_amount" in thresholds:
            max_amount = thresholds["total_amount"]
            time_window_hours = thresholds.get("time_window_hours", 24)

            cutoff_time = utc_now() - timedelta(hours=time_window_hours)
            total = sum(tx.amount for tx in transactions if tx.timestamp >= cutoff_time)

            if total > max_amount:
                return True

        # Average amount deviation
        if "average_deviation_percent" in thresholds:
            user_profile = self.db.query(UserRiskProfile).filter(
                UserRiskProfile.user_id == user_id
            ).first()

            if user_profile and user_profile.average_transaction_amount:
                avg_threshold = thresholds["average_deviation_percent"]
                baseline = user_profile.average_transaction_amount

                for tx in transactions:
                    deviation = abs(tx.amount - baseline) / baseline * 100
                    if deviation > avg_threshold:
                        return True

        return False

    def _create_velocity_alert(
        self,
        transactions: List[Transaction],
        rule: MonitoringRule,
        user_id: str
    ) -> Alert:
        """
        Create an alert for velocity rule violation.
        """
        alert_id = f"ALT-{utc_now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

        # Calculate statistics
        total_amount = sum(tx.amount for tx in transactions)
        transaction_count = len(transactions)

        evidence = {
            "rule_id": rule.rule_id,
            "rule_name": rule.name,
            "transaction_count": transaction_count,
            "total_amount": float(total_amount),
            "time_window": "24 hours",
            "transactions": [tx.transaction_id for tx in transactions[:10]]  # First 10
        }

        # Get regulatory context if available
        regulation_context = None
        related_regulations = []

        if rule.regulatory_source_id:
            legal_doc = self.db.query(LegalDocument).filter(
                LegalDocument.id == rule.regulatory_source_id
            ).first()

            if legal_doc:
                related_regulations = [legal_doc.id]
                regulation_context = f"Velocity monitoring required by {legal_doc.celex}: {rule.regulatory_requirement}"

        alert = Alert(
            tenant_id=transactions[0].tenant_id,
            alert_id=alert_id,
            alert_type='velocity',
            severity=rule.severity,
            transaction_id=None,  # Multiple transactions
            user_id=user_id,
            status='pending',
            priority=self._calculate_priority(rule.severity),
            description=f"Velocity rule triggered: {rule.name} - {transaction_count} transactions totaling {total_amount}",
            risk_score=min(100, transaction_count * 5),  # Simple scoring
            matched_rules_data={rule.rule_id: rule.name},
            evidence=evidence,
            related_regulations=related_regulations,
            regulation_context=regulation_context
        )

        self.db.add(alert)

        logger.info(f"Velocity alert {alert_id} created for user {user_id}")

        return alert


class RuleBuilder:
    """
    Helper class to build monitoring rules from regulations.

    YUFEED INNOVATION: Auto-generates rules from EU regulatory text.
    """

    @staticmethod
    def create_transaction_limit_rule(
        name: str,
        amount_limit: Decimal,
        currency: str = "EUR",
        regulatory_source_id: Optional[int] = None,
        regulation_article: Optional[str] = None,
        regulatory_requirement: Optional[str] = None,
        severity: str = "medium"
    ) -> Dict[str, Any]:
        """
        Create a rule for transaction amount limits.

        Example: "Transactions over €10,000 require enhanced due diligence"
        """
        return {
            "name": name,
            "category": "amount_threshold",
            "severity": severity,
            "conditions": {
                "conditions": [
                    {
                        "field": "amount",
                        "operator": "greater_than",
                        "value": float(amount_limit)
                    },
                    {
                        "field": "currency",
                        "operator": "equals",
                        "value": currency
                    }
                ],
                "logic": "AND"
            },
            "regulatory_source_id": regulatory_source_id,
            "regulation_article": regulation_article,
            "regulatory_requirement": regulatory_requirement
        }

    @staticmethod
    def create_high_risk_country_rule(
        name: str,
        country_codes: List[str],
        regulatory_source_id: Optional[int] = None,
        regulation_article: Optional[str] = None,
        severity: str = "high"
    ) -> Dict[str, Any]:
        """
        Create a rule for high-risk jurisdiction transactions.

        Example: "Transactions with sanctioned countries"
        """
        return {
            "name": name,
            "category": "sanctions",
            "severity": severity,
            "conditions": {
                "conditions": [
                    {
                        "field": "country_code",
                        "operator": "in",
                        "value": country_codes
                    }
                ],
                "logic": "AND"
            },
            "regulatory_source_id": regulatory_source_id,
            "regulation_article": regulation_article,
            "regulatory_requirement": "OFAC/EU sanctions compliance"
        }

    @staticmethod
    def create_velocity_rule(
        name: str,
        max_transactions: int,
        time_window_hours: int = 24,
        regulatory_source_id: Optional[int] = None,
        severity: str = "medium"
    ) -> Dict[str, Any]:
        """
        Create a velocity rule for transaction frequency.

        Example: "More than 10 transactions in 24 hours"
        """
        return {
            "name": name,
            "category": "velocity",
            "severity": severity,
            "conditions": {
                "conditions": [],  # Evaluated differently
                "logic": "AND"
            },
            "thresholds": {
                "transaction_count": max_transactions,
                "time_window_hours": time_window_hours
            },
            "regulatory_source_id": regulatory_source_id,
            "regulatory_requirement": "AML transaction monitoring"
        }
