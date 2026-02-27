"""add performance indexes for feature computation and monitoring

Revision ID: 20260206_indexes
Revises: 20260206_ai_usage
Create Date: 2026-02-06

Adds composite indexes for:
- Feature computation queries (velocity, volume, geographic diversity)
- Transaction processing lookups
- Monitoring and alerting queries
- Rules engine evaluations
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260206_indexes"
down_revision = "20260206_ai_usage"
branch_labels = None
depends_on = None


def upgrade():
    # ============================================================================
    # Transaction Table Indexes (Feature Computation)
    # ============================================================================

    # Composite index for velocity queries
    # Used by: _calculate_velocity() in feature_computation.py
    op.create_index(
        "idx_txn_tenant_user_timestamp",
        "transactions",
        ["tenant_id", "user_id", "timestamp"],
        postgresql_using="btree",
        unique=False,
    )

    # Index for volume/avg queries (with status filter)
    # Used by: _calculate_total_volume(), _calculate_avg_amount()
    op.create_index(
        "idx_txn_tenant_user_status_timestamp",
        "transactions",
        ["tenant_id", "user_id", "status", "timestamp"],
        postgresql_using="btree",
        unique=False,
    )

    # Index for country uniqueness queries
    # Used by: _count_unique_countries()
    op.create_index(
        "idx_txn_tenant_user_country",
        "transactions",
        ["tenant_id", "user_id", "country_code", "timestamp"],
        postgresql_using="btree",
        unique=False,
    )

    # Index for risk queries
    # Used by: _count_high_risk_transactions()
    op.create_index(
        "idx_txn_tenant_user_risk",
        "transactions",
        ["tenant_id", "user_id", "risk_score", "timestamp"],
        postgresql_using="btree",
        unique=False,
    )

    # ============================================================================
    # Alerts Table Indexes (Monitoring)
    # ============================================================================

    # Composite index for alert filtering
    op.create_index(
        "idx_alert_tenant_status_created",
        "alerts",
        ["tenant_id", "status", "created_at"],
        postgresql_using="btree",
        unique=False,
    )

    # Index for user-specific alerts
    op.create_index(
        "idx_alert_tenant_user",
        "alerts",
        ["tenant_id", "user_id"],
        postgresql_using="btree",
        unique=False,
    )

    # Index for severity filtering
    op.create_index(
        "idx_alert_tenant_severity",
        "alerts",
        ["tenant_id", "severity"],
        postgresql_using="btree",
        unique=False,
    )

    # ============================================================================
    # Rules Table Indexes (Rules Engine)
    # ============================================================================

    # Index for active rules queries
    op.create_index(
        "idx_rules_tenant_active",
        "monitoring_rules",
        ["tenant_id", "enabled"],
        postgresql_using="btree",
        unique=False,
    )

    # ============================================================================
    # Feature Values Table Indexes
    # ============================================================================

    # Composite index for feature lookups.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_feature_tenant_entity
        ON feature_values (tenant_id, entity_type, entity_id)
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_feature_tenant_updated
        ON feature_values (tenant_id, calculated_at)
        """
    )

    # ============================================================================
    # Cases Table Indexes (Case Management)
    # ============================================================================

    # Index for case filtering by status
    op.create_index(
        "idx_cases_tenant_status",
        "cases",
        ["tenant_id", "status"],
        postgresql_using="btree",
        unique=False,
    )

    # ============================================================================
    # Regulatory Obligations Table Indexes (Compliance)
    # ============================================================================

    # Index for obligation filtering by status
    op.create_index(
        "idx_reg_obligations_status",
        "regulatory_obligations",
        ["status", "created_at"],
        postgresql_using="btree",
        unique=False,
    )

    # Index for policy-to-obligation lookups
    op.create_index(
        "idx_reg_obligations_policy",
        "regulatory_obligations",
        ["linked_policy_id"],
        postgresql_using="btree",
        unique=False,
    )

    # ============================================================================
    # Watchlists Table Indexes
    # ============================================================================

    # Note: watchlists table doesn't have watchlist_id FK structure
    # Skipping watchlist_entries index (table doesn't exist in current schema)


def downgrade():
    # Drop indexes in reverse order
    op.drop_index("idx_reg_obligations_policy", "regulatory_obligations")
    op.drop_index("idx_reg_obligations_status", "regulatory_obligations")
    op.drop_index("idx_cases_tenant_status", "cases")

    # Feature values indexes
    op.execute("DROP INDEX IF EXISTS idx_feature_tenant_updated")
    op.execute("DROP INDEX IF EXISTS idx_feature_tenant_entity")

    op.drop_index("idx_rules_tenant_active", "monitoring_rules")
    op.drop_index("idx_alert_tenant_severity", "alerts")
    op.drop_index("idx_alert_tenant_user", "alerts")
    op.drop_index("idx_alert_tenant_status_created", "alerts")
    op.drop_index("idx_txn_tenant_user_risk", "transactions")
    op.drop_index("idx_txn_tenant_user_country", "transactions")
    op.drop_index("idx_txn_tenant_user_status_timestamp", "transactions")
    op.drop_index("idx_txn_tenant_user_timestamp", "transactions")
