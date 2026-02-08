"""add_transaction_monitoring_schema

Revision ID: c62fa69a5718
Revises: b059980f41d9
Create Date: 2026-01-08 08:28:25.090553

Phase 1: Transaction Monitoring Foundation
- Transactions table
- Alerts table
- Cases table
- Monitoring Rules table
- User Risk Profiles table
- Feature Values table (simplified feature store)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c62fa69a5718"
down_revision: Union[str, Sequence[str], None] = "b059980f41d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add transaction monitoring tables."""
    bind = op.get_bind()
    dialect = bind.dialect.name
    json_type = postgresql.JSONB() if dialect == "postgresql" else sa.JSON()
    inet_type = postgresql.INET() if dialect == "postgresql" else sa.String(45)
    array_int = postgresql.ARRAY(sa.Integer) if dialect == "postgresql" else sa.JSON()
    array_str = postgresql.ARRAY(sa.String(255)) if dialect == "postgresql" else sa.JSON()
    array_str2 = postgresql.ARRAY(sa.String(2)) if dialect == "postgresql" else sa.JSON()

    # 1. Transactions table
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("transaction_id", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("user_id", sa.String(255), nullable=False, index=True),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column(
            "transaction_type", sa.String(50)
        ),  # 'deposit', 'withdrawal', 'transfer', 'payment'
        sa.Column("counterparty_id", sa.String(255)),
        sa.Column("counterparty_name", sa.String(500)),
        sa.Column("timestamp", sa.DateTime(), nullable=False, index=True),
        sa.Column(
            "status", sa.String(50), default="completed"
        ),  # 'pending', 'completed', 'flagged', 'blocked'
        # Geographic data
        sa.Column("ip_address", inet_type),
        sa.Column("country_code", sa.String(2)),
        sa.Column("geo_location", sa.String(255)),
        # Risk data
        sa.Column("risk_score", sa.Numeric(5, 2)),
        sa.Column("risk_level", sa.String(20)),  # 'low', 'medium', 'high', 'critical'
        sa.Column("risk_factors", json_type),
        # Metadata
        sa.Column("device_fingerprint", sa.String(255)),
        sa.Column("session_id", sa.String(255)),
        sa.Column("metadata", json_type),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()
        ),
    )

    # Indexes for transactions
    op.create_index("ix_transactions_user_timestamp", "transactions", ["user_id", "timestamp"])
    op.create_index("ix_transactions_risk_level", "transactions", ["risk_level"])
    op.create_index("ix_transactions_country", "transactions", ["country_code"])
    op.create_index("ix_transactions_amount", "transactions", ["amount"])

    # 2. Alerts table
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("alert_id", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column(
            "alert_type", sa.String(100), nullable=False
        ),  # 'velocity', 'structuring', 'unusual_pattern', etc.
        sa.Column("severity", sa.String(20), nullable=False),  # 'low', 'medium', 'high', 'critical'
        # Triggered by
        sa.Column("transaction_id", sa.Integer(), sa.ForeignKey("transactions.id"), nullable=True),
        sa.Column("user_id", sa.String(255), index=True),
        sa.Column("rule_id", sa.String(255)),
        # Status workflow
        sa.Column(
            "status", sa.String(50), default="pending"
        ),  # 'pending', 'in_review', 'escalated', 'resolved', 'false_positive'
        sa.Column("assigned_to", sa.String(255)),
        sa.Column("priority", sa.Integer(), default=3),  # 1 (highest) to 5 (lowest)
        # Alert details
        sa.Column("description", sa.Text()),
        sa.Column("risk_score", sa.Numeric(5, 2)),
        sa.Column("matched_rules", json_type),
        sa.Column("evidence", json_type),
        # REGULATORY CONTEXT (Yufeed Innovation)
        sa.Column("related_regulations", json_type),  # Array of LegalDocument IDs
        sa.Column("regulation_context", sa.Text()),  # AI-generated explanation
        # Resolution
        sa.Column("resolution_status", sa.String(50)),
        sa.Column("resolution_notes", sa.Text()),
        sa.Column("resolved_by", sa.String(255)),
        sa.Column("resolved_at", sa.DateTime()),
        # SAR filing
        sa.Column("sar_filed", sa.Boolean(), default=False),
        sa.Column("sar_id", sa.String(255)),
        sa.Column("sar_filed_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()
        ),
    )

    # Indexes for alerts
    op.create_index("ix_alerts_status", "alerts", ["status"])
    op.create_index("ix_alerts_severity", "alerts", ["severity"])
    op.create_index("ix_alerts_user", "alerts", ["user_id"])
    op.create_index("ix_alerts_created", "alerts", ["created_at"])
    op.create_index("ix_alerts_assigned", "alerts", ["assigned_to"])

    # 3. Cases table
    op.create_table(
        "cases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("case_id", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("case_type", sa.String(100)),  # 'investigation', 'sar_preparation', 'audit'
        sa.Column("subject_type", sa.String(50)),  # 'user', 'transaction', 'pattern'
        sa.Column("subject_id", sa.String(255), index=True),
        # Status
        sa.Column(
            "status", sa.String(50), default="open"
        ),  # 'open', 'in_progress', 'escalated', 'closed'
        sa.Column(
            "priority", sa.String(20), default="medium"
        ),  # 'low', 'medium', 'high', 'critical'
        # Assignment
        sa.Column("assigned_to", sa.String(255)),
        sa.Column("team", sa.String(100)),
        # Content
        sa.Column("title", sa.String(500)),
        sa.Column("description", sa.Text()),
        sa.Column("summary", sa.Text()),
        # Related entities (using PostgreSQL arrays)
        sa.Column("related_alert_ids", array_int),
        sa.Column("related_transaction_ids", array_int),
        sa.Column("related_users", array_str),
        # REGULATORY LINKAGE (Yufeed Innovation)
        sa.Column("applicable_regulation_ids", array_int),  # LegalDocument IDs
        sa.Column("regulatory_violations", json_type),
        # Evidence
        sa.Column("evidence", json_type),
        sa.Column("attachments", json_type),
        # Timeline
        sa.Column("opened_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime()),
        # Outcomes
        sa.Column(
            "outcome", sa.String(100)
        ),  # 'sar_filed', 'no_action', 'account_closed', 'escalated'
        sa.Column("outcome_notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()
        ),
    )

    # Indexes for cases
    op.create_index("ix_cases_status", "cases", ["status"])
    op.create_index("ix_cases_priority", "cases", ["priority"])
    op.create_index("ix_cases_assigned", "cases", ["assigned_to"])
    op.create_index("ix_cases_subject", "cases", ["subject_id"])

    # 4. Monitoring Rules table
    op.create_table(
        "monitoring_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rule_id", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("description", sa.Text()),
        # Rule type
        sa.Column(
            "category", sa.String(100)
        ),  # 'velocity', 'structuring', 'unusual_behavior', 'sanctions'
        sa.Column("severity", sa.String(20), default="medium"),
        # Rule logic (JSON-based DSL)
        sa.Column("conditions", json_type, nullable=False),
        sa.Column("thresholds", json_type),
        # Regulatory basis (YUFEED INNOVATION)
        sa.Column(
            "regulatory_source_id", sa.Integer(), sa.ForeignKey("legal_documents.id"), nullable=True
        ),
        sa.Column("regulation_article", sa.String(255)),
        sa.Column("regulatory_requirement", sa.Text()),
        # Status
        sa.Column("enabled", sa.Boolean(), default=True),
        sa.Column("version", sa.Integer(), default=1),
        # Performance tracking
        sa.Column("alert_count", sa.Integer(), default=0),
        sa.Column("true_positive_rate", sa.Numeric(5, 2)),
        sa.Column("false_positive_rate", sa.Numeric(5, 2)),
        sa.Column("created_by", sa.String(255)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()
        ),
    )

    # Indexes for monitoring rules
    op.create_index("ix_monitoring_rules_enabled", "monitoring_rules", ["enabled"])
    op.create_index("ix_monitoring_rules_category", "monitoring_rules", ["category"])

    # 5. User Risk Profiles table
    op.create_table(
        "user_risk_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(255), unique=True, nullable=False, index=True),
        # Computed risk
        sa.Column("overall_risk_score", sa.Numeric(5, 2)),
        sa.Column("risk_level", sa.String(20)),  # 'low', 'medium', 'high', 'critical'
        sa.Column("risk_factors", json_type),
        # Behavioral patterns
        sa.Column("transaction_velocity_30d", sa.Integer()),
        sa.Column("average_transaction_amount", sa.Numeric(15, 2)),
        sa.Column("total_transaction_amount_30d", sa.Numeric(15, 2)),
        sa.Column("transaction_pattern_score", sa.Numeric(5, 2)),
        # KYC/CDD status
        sa.Column("kyc_status", sa.String(50)),
        sa.Column("kyc_last_updated", sa.DateTime()),
        sa.Column("enhanced_due_diligence", sa.Boolean(), default=False),
        # Geographic risk
        sa.Column("primary_country", sa.String(2)),
        sa.Column("high_risk_jurisdictions", array_str2),
        # Alerts history
        sa.Column("total_alerts", sa.Integer(), default=0),
        sa.Column("critical_alerts", sa.Integer(), default=0),
        sa.Column("resolved_alerts", sa.Integer(), default=0),
        # Sanctions screening
        sa.Column("sanctions_screened_at", sa.DateTime()),
        sa.Column("sanctions_match", sa.Boolean(), default=False),
        sa.Column("sanctions_details", json_type),
        # Account metadata
        sa.Column("account_created_at", sa.DateTime()),
        sa.Column("last_activity_at", sa.DateTime()),
        sa.Column("last_calculated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()
        ),
    )

    # Indexes for user risk profiles
    op.create_index("ix_user_risk_profiles_risk_level", "user_risk_profiles", ["risk_level"])
    op.create_index(
        "ix_user_risk_profiles_risk_score", "user_risk_profiles", ["overall_risk_score"]
    )

    # 6. Feature Values table (Simplified Feature Store)
    op.create_table(
        "feature_values",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_type", sa.String(50), nullable=False),  # 'transaction', 'user', 'session'
        sa.Column("entity_id", sa.String(255), nullable=False),
        # Feature data
        sa.Column("feature_name", sa.String(255), nullable=False),
        sa.Column("feature_value", json_type, nullable=False),
        sa.Column("feature_type", sa.String(50)),  # 'numeric', 'categorical', 'boolean', 'text'
        # Metadata
        sa.Column("calculated_at", sa.DateTime(), nullable=False),
        sa.Column("version", sa.Integer(), default=1),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # Indexes for feature values (critical for fast lookups)
    op.create_index(
        "ix_feature_values_lookup", "feature_values", ["entity_type", "entity_id", "feature_name"]
    )
    op.create_index("ix_feature_values_entity", "feature_values", ["entity_type", "entity_id"])


def downgrade() -> None:
    """Downgrade schema - Remove transaction monitoring tables."""
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table("feature_values")
    op.drop_table("user_risk_profiles")
    op.drop_table("monitoring_rules")
    op.drop_table("cases")
    op.drop_table("alerts")
    op.drop_table("transactions")
