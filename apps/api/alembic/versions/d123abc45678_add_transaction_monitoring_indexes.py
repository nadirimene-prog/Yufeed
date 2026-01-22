"""add_transaction_monitoring_indexes

Revision ID: d123abc45678
Revises: c62fa69a5718
Create Date: 2026-01-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd123abc45678'
down_revision: Union[str, Sequence[str], None] = 'c62fa69a5718'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add performance indexes for transaction monitoring."""

    # Transaction indexes
    op.create_index('ix_transactions_country_code', 'transactions', ['country_code'])
    op.create_index('ix_transactions_risk_level', 'transactions', ['risk_level'])

    # Alert indexes
    op.create_index('ix_alerts_transaction_id', 'alerts', ['transaction_id'])
    op.create_index('ix_alerts_status', 'alerts', ['status'])
    op.create_index('ix_alerts_assigned_to', 'alerts', ['assigned_to'])
    op.create_index('ix_alerts_sar_filed', 'alerts', ['sar_filed'])
    op.create_index('ix_alerts_created_at', 'alerts', ['created_at'])

    # Case indexes
    op.create_index('ix_cases_status', 'cases', ['status'])
    op.create_index('ix_cases_priority', 'cases', ['priority'])
    op.create_index('ix_cases_assigned_to', 'cases', ['assigned_to'])

    # Composite indexes for common query patterns
    op.create_index('ix_alerts_status_severity', 'alerts', ['status', 'severity'])
    op.create_index('ix_alerts_user_status', 'alerts', ['user_id', 'status'])
    op.create_index('ix_transactions_user_timestamp', 'transactions', ['user_id', 'timestamp'])


def downgrade() -> None:
    """Downgrade schema - Remove transaction monitoring indexes."""

    # Drop composite indexes
    op.drop_index('ix_transactions_user_timestamp', 'transactions')
    op.drop_index('ix_alerts_user_status', 'alerts')
    op.drop_index('ix_alerts_status_severity', 'alerts')

    # Drop case indexes
    op.drop_index('ix_cases_assigned_to', 'cases')
    op.drop_index('ix_cases_priority', 'cases')
    op.drop_index('ix_cases_status', 'cases')

    # Drop alert indexes
    op.drop_index('ix_alerts_created_at', 'alerts')
    op.drop_index('ix_alerts_sar_filed', 'alerts')
    op.drop_index('ix_alerts_assigned_to', 'alerts')
    op.drop_index('ix_alerts_status', 'alerts')
    op.drop_index('ix_alerts_transaction_id', 'alerts')

    # Drop transaction indexes
    op.drop_index('ix_transactions_risk_level', 'transactions')
    op.drop_index('ix_transactions_country_code', 'transactions')
