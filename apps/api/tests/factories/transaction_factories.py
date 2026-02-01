"""
Factory Boy factories for transaction monitoring models.
"""
import factory
from factory.faker import Faker
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

from src.models.transaction_models import (
    Transaction,
    Alert,
    Case,
    MonitoringRule,
    RuleHit,
)

class BaseSQLAlchemyFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Base factory that accepts sqlalchemy_session in create kwargs."""

    class Meta:
        abstract = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        session = kwargs.pop("sqlalchemy_session", None)
        if session is not None:
            cls._meta.sqlalchemy_session = session
        return super()._create(model_class, *args, **kwargs)


class TransactionFactory(BaseSQLAlchemyFactory):
    """Factory for creating test Transaction instances."""

    class Meta:
        model = Transaction
        sqlalchemy_session_persistence = "commit"

    tenant_id = factory.LazyFunction(lambda: "default")
    transaction_id = factory.LazyFunction(lambda: f"txn_{uuid.uuid4().hex[:12]}")
    user_id = factory.LazyFunction(lambda: f"user_{uuid.uuid4().hex[:8]}")
    amount = factory.Faker("pydecimal", left_digits=5, right_digits=2, positive=True, min_value=1, max_value=100000)
    currency = factory.Faker("random_element", elements=["USD", "EUR", "GBP", "BTC", "ETH"])
    transaction_type = factory.Faker("random_element", elements=["deposit", "withdrawal", "transfer", "payment"])
    counterparty_id = factory.LazyFunction(lambda: f"user_{uuid.uuid4().hex[:8]}")
    counterparty_name = factory.Faker("company")
    timestamp = factory.Faker("date_time_between", start_date="-30d", end_date="now")
    status = factory.Faker("random_element", elements=["completed", "pending", "flagged", "blocked"])

    # Geographic data
    ip_address = factory.Faker("ipv4")
    country_code = factory.Faker("country_code")
    geo_location = factory.Faker("city")

    # Risk data
    risk_score = factory.Faker("pydecimal", left_digits=2, right_digits=2, positive=True, min_value=1, max_value=100)
    risk_level = factory.Faker("random_element", elements=["low", "medium", "high", "critical"])
    risk_factors = factory.LazyFunction(lambda: {
        "velocity": "high",
        "unusual_pattern": True,
        "country_risk": "medium"
    })

    # Metadata
    device_fingerprint = factory.Faker("sha256")
    session_id = factory.LazyFunction(lambda: f"sess_{uuid.uuid4().hex[:16]}")
    transaction_metadata = factory.LazyFunction(lambda: {
        "payment_method": "bank_transfer",
        "ip_country": "US",
        "user_agent": "Mozilla/5.0"
    })
    description = factory.Faker("sentence")

    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class AlertFactory(BaseSQLAlchemyFactory):
    """Factory for creating test Alert instances."""

    class Meta:
        model = Alert
        sqlalchemy_session_persistence = "commit"

    tenant_id = factory.LazyAttribute(lambda obj: obj.transaction.tenant_id if obj.transaction else "default")
    alert_id = factory.LazyFunction(lambda: f"alert_{uuid.uuid4().hex[:12]}")
    alert_type = factory.Faker("random_element", elements=[
        "velocity",
        "structuring",
        "unusual_pattern",
        "high_value",
        "sanctions",
        "country_risk"
    ])
    severity = factory.Faker("random_element", elements=["low", "medium", "high", "critical"])

    # Transaction relationship (optional)
    transaction = factory.SubFactory(TransactionFactory)
    user_id = factory.LazyAttribute(lambda obj: obj.transaction.user_id if obj.transaction else f"user_{uuid.uuid4().hex[:8]}")

    # Status workflow
    status = factory.Faker("random_element", elements=["pending", "in_review", "resolved", "false_positive", "escalated"])
    assigned_to = factory.Faker("email")
    priority = factory.Faker("random_int", min=1, max=5)

    # Alert details
    description = factory.Faker("paragraph")
    risk_score = factory.Faker("pydecimal", left_digits=2, right_digits=2, positive=True, min_value=1, max_value=100)
    matched_rules_data = factory.LazyFunction(lambda: {
        "rule_001": {"rule_name": "High Value Transaction", "matched": True}
    })
    evidence = factory.LazyFunction(lambda: {
        "transactions": ["txn_001", "txn_002"],
        "patterns": ["rapid_succession", "round_amounts"]
    })

    # Regulatory context
    related_regulations = factory.LazyFunction(lambda: [1, 2])
    regulation_context = factory.Faker("paragraph")

    # Resolution
    resolution_status = None
    resolution_notes = None
    resolved_by = None
    resolved_at = None

    # SAR filing
    sar_filed = False
    sar_id = None
    sar_filed_at = None

    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class CaseFactory(BaseSQLAlchemyFactory):
    """Factory for creating test Case instances."""

    class Meta:
        model = Case
        sqlalchemy_session_persistence = "commit"

    tenant_id = factory.LazyFunction(lambda: "default")
    case_id = factory.LazyFunction(lambda: f"case_{uuid.uuid4().hex[:12]}")
    case_type = factory.Faker("random_element", elements=["investigation", "sar_preparation", "audit"])
    subject_type = factory.Faker("random_element", elements=["user", "transaction", "pattern"])
    subject_id = factory.LazyFunction(lambda: f"subject_{uuid.uuid4().hex[:8]}")

    # Status
    status = factory.Faker("random_element", elements=["open", "in_progress", "closed", "escalated"])
    priority = factory.Faker("random_element", elements=["low", "medium", "high", "critical"])

    # Assignment
    assigned_to = factory.Faker("email")
    team = factory.Faker("random_element", elements=["compliance", "investigations", "aml"])

    # Content
    title = factory.Faker("sentence")
    description = factory.Faker("paragraph")
    summary = factory.Faker("text")

    # Related entities
    related_alert_ids = factory.LazyFunction(lambda: [1, 2, 3])
    related_transaction_ids = factory.LazyFunction(lambda: [10, 11, 12])
    related_users = factory.LazyFunction(lambda: [f"user_{i}" for i in range(1, 4)])

    # Regulatory linkage
    applicable_regulation_ids = factory.LazyFunction(lambda: [1, 2])
    regulatory_violations = factory.LazyFunction(lambda: {
        "violation_type": "structuring",
        "severity": "high",
        "regulations": ["BSA", "6AMLD"]
    })

    # Evidence
    evidence = factory.LazyFunction(lambda: {
        "documents": ["doc1.pdf", "doc2.pdf"],
        "screenshots": ["screen1.png"]
    })
    attachments = factory.LazyFunction(lambda: [])

    # Timeline
    opened_at = factory.LazyFunction(datetime.utcnow)
    closed_at = None

    # Outcomes
    outcome = None
    outcome_notes = None

    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class MonitoringRuleFactory(BaseSQLAlchemyFactory):
    """Factory for creating test MonitoringRule instances."""

    class Meta:
        model = MonitoringRule
        sqlalchemy_session_persistence = "commit"

    tenant_id = factory.LazyFunction(lambda: "default")
    rule_id = factory.LazyFunction(lambda: f"rule_{uuid.uuid4().hex[:12]}")
    name = factory.Faker("sentence")
    description = factory.Faker("paragraph")

    # Rule type and priority
    category = factory.Faker("random_element", elements=[
        "velocity",
        "structuring",
        "unusual_behavior",
        "sanctions",
        "high_value"
    ])
    severity = factory.Faker("random_element", elements=["low", "medium", "high", "critical"])
    priority = factory.Faker("random_int", min=1, max=5)

    # Rule logic
    conditions = factory.LazyFunction(lambda: {
        "logic": "AND",
        "conditions": [
            {"field": "amount", "operator": ">", "value": 10000},
            {"field": "currency", "operator": "==", "value": "USD"}
        ]
    })

    # Aggregation requirements
    thresholds = factory.LazyFunction(lambda: {
        "window_size": "24h",
        "metric": "sum",
        "field": "amount",
        "threshold": 50000
    })

    # Regulatory basis
    regulatory_source_id = None
    regulation_article = factory.Faker("bothify", text="Article ##")
    regulatory_requirement = factory.Faker("sentence")

    # Status and Versioning
    enabled = True
    is_template = False
    version = 1

    # Performance tracking
    alert_count = 0
    true_positive_rate = None
    false_positive_rate = None

    created_by = factory.Faker("email")
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class RuleHitFactory(BaseSQLAlchemyFactory):
    """Factory for creating test RuleHit instances."""

    class Meta:
        model = RuleHit
        sqlalchemy_session_persistence = "commit"

    tenant_id = factory.LazyAttribute(lambda obj: obj.alert.tenant_id if obj.alert else "default")
    alert = factory.SubFactory(AlertFactory)
    rule = factory.SubFactory(MonitoringRuleFactory)

    matched_conditions = factory.LazyFunction(lambda: {
        "amount": {"expected": ">10000", "actual": 15000, "matched": True},
        "currency": {"expected": "USD", "actual": "USD", "matched": True}
    })

    computed_features = factory.LazyFunction(lambda: {
        "velocity_24h": 5,
        "total_amount_24h": 75000,
        "unique_counterparties_24h": 3
    })

    triggered_at = factory.LazyFunction(datetime.utcnow)
