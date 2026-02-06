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
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260206_indexes'
down_revision = '20260206_ai_usage'
branch_labels = None
depends_on = None


def upgrade():
    # ============================================================================
    # Transaction Table Indexes (Feature Computation)
    # ============================================================================

    # Composite index for velocity queries
    # Used by: _calculate_velocity() in feature_computation.py
    op.create_index(
        'idx_txn_tenant_user_timestamp',
        'transactions',
        ['tenant_id', 'user_id', 'timestamp'],
        postgresql_using='btree',
        unique=False
    )

    # Index for volume/avg queries (with status filter)
    # Used by: _calculate_total_volume(), _calculate_avg_amount()
    op.create_index(
        'idx_txn_tenant_user_status_timestamp',
        'transactions',
        ['tenant_id', 'user_id', 'status', 'timestamp'],
        postgresql_using='btree',
        unique=False
    )

    # Index for country uniqueness queries
    # Used by: _count_unique_countries()
    op.create_index(
        'idx_txn_tenant_user_country',
        'transactions',
        ['tenant_id', 'user_id', 'country_code', 'timestamp'],
        postgresql_using='btree',
        unique=False
    )

    # Index for risk queries
    # Used by: _count_high_risk_transactions()
    op.create_index(
        'idx_txn_tenant_user_risk',
        'transactions',
        ['tenant_id', 'user_id', 'risk_score', 'timestamp'],
        postgresql_using='btree',
        unique=False
    )

    # ============================================================================
    # Alerts Table Indexes (Monitoring)
    # ============================================================================

    # Composite index for alert filtering
    op.create_index(
        'idx_alert_tenant_status_created',
        'alerts',
        ['tenant_id', 'status', 'created_at'],
        postgresql_using='btree',
        unique=False
    )

    # Index for user-specific alerts
    op.create_index(
        'idx_alert_tenant_user',
        'alerts',
        ['tenant_id', 'user_id'],
        postgresql_using='btree',
        unique=False
    )

    # Index for severity filtering
    op.create_index(
        'idx_alert_tenant_severity',
        'alerts',
        ['tenant_id', 'severity'],
        postgresql_using='btree',
        unique=False
    )

    # ============================================================================
    # Rules Table Indexes (Rules Engine)
    # ============================================================================

    # Index for active rules queries
    op.create_index(
        'idx_rules_tenant_active',
        'monitoring_rules',
        ['tenant_id', 'is_active'],
        postgresql_using='btree',
        unique=False
    )

    # ============================================================================
    # Feature Values Table Indexes
    # ============================================================================

    # Composite index for feature lookups (if not already exists from Week 2 B7)
    # Check if index exists first
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('feature_values')]

    if 'idx_feature_tenant_entity' not in existing_indexes:
        op.create_index(
            'idx_feature_tenant_entity',
            'feature_values',
            ['tenant_id', 'entity_type', 'entity_id'],
            postgresql_using='btree',
            unique=False
        )

    if 'idx_feature_tenant_updated' not in existing_indexes:
        op.create_index(
            'idx_feature_tenant_updated',
            'feature_values',
            ['tenant_id', 'updated_at'],
            postgresql_using='btree',
            unique=False
        )

    # ============================================================================
    # Cases Table Indexes (Case Management)
    # ============================================================================

    # Index for case filtering by status
    op.create_index(
        'idx_cases_tenant_status',
        'cases',
        ['tenant_id', 'status'],
        postgresql_using='btree',
        unique=False
    )

    # ============================================================================
    # Obligations Table Indexes (Compliance)
    # ============================================================================

    # Index for obligation filtering by status
    op.create_index(
        'idx_obligations_tenant_status',
        'obligations',
        ['tenant_id', 'status'],
        postgresql_using='btree',
        unique=False
    )

    # Index for policy-to-obligation lookups
    op.create_index(
        'idx_obligations_policy',
        'obligations',
        ['policy_id'],
        postgresql_using='btree',
        unique=False
    )

    # ============================================================================
    # Watchlists Table Indexes
    # ============================================================================

    # Index for watchlist entries lookup
    op.create_index(
        'idx_watchlist_entries_watchlist',
        'watchlist_entries',
        ['watchlist_id'],
        postgresql_using='btree',
        unique=False
    )


def downgrade():
    # Drop indexes in reverse order
    op.drop_index('idx_watchlist_entries_watchlist', 'watchlist_entries')
    op.drop_index('idx_obligations_policy', 'obligations')
    op.drop_index('idx_obligations_tenant_status', 'obligations')
    op.drop_index('idx_cases_tenant_status', 'cases')

    # Feature values indexes (only if we created them)
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('feature_values')]

    if 'idx_feature_tenant_updated' in existing_indexes:
        op.drop_index('idx_feature_tenant_updated', 'feature_values')

    if 'idx_feature_tenant_entity' in existing_indexes:
        op.drop_index('idx_feature_tenant_entity', 'feature_values')

    op.drop_index('idx_rules_tenant_active', 'monitoring_rules')
    op.drop_index('idx_alert_tenant_severity', 'alerts')
    op.drop_index('idx_alert_tenant_user', 'alerts')
    op.drop_index('idx_alert_tenant_status_created', 'alerts')
    op.drop_index('idx_txn_tenant_user_risk', 'transactions')
    op.drop_index('idx_txn_tenant_user_country', 'transactions')
    op.drop_index('idx_txn_tenant_user_status_timestamp', 'transactions')
    op.drop_index('idx_txn_tenant_user_timestamp', 'transactions')
