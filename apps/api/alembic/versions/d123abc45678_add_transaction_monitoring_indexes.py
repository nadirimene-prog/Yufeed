"""add_transaction_monitoring_indexes

Revision ID: d123abc45678
Revises: c62fa69a5718
Create Date: 2026-01-19 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d123abc45678"
down_revision: Union[str, Sequence[str], None] = "c62fa69a5718"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add performance indexes for transaction monitoring."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    def _existing_indexes(table: str) -> set:
        return {idx["name"] for idx in inspector.get_indexes(table)}

    def _create_index(name: str, table: str, columns: list):
        if name not in _existing_indexes(table):
            op.create_index(name, table, columns)

    # Transaction indexes
    _create_index("ix_transactions_country_code", "transactions", ["country_code"])
    _create_index("ix_transactions_risk_level", "transactions", ["risk_level"])

    # Alert indexes
    _create_index("ix_alerts_transaction_id", "alerts", ["transaction_id"])
    _create_index("ix_alerts_status", "alerts", ["status"])
    _create_index("ix_alerts_assigned_to", "alerts", ["assigned_to"])
    _create_index("ix_alerts_sar_filed", "alerts", ["sar_filed"])
    _create_index("ix_alerts_created_at", "alerts", ["created_at"])

    # Case indexes
    _create_index("ix_cases_status", "cases", ["status"])
    _create_index("ix_cases_priority", "cases", ["priority"])
    _create_index("ix_cases_assigned_to", "cases", ["assigned_to"])

    # Composite indexes for common query patterns
    _create_index("ix_alerts_status_severity", "alerts", ["status", "severity"])
    _create_index("ix_alerts_user_status", "alerts", ["user_id", "status"])
    _create_index("ix_transactions_user_timestamp", "transactions", ["user_id", "timestamp"])


def downgrade() -> None:
    """Downgrade schema - Remove transaction monitoring indexes."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    def _existing_indexes(table: str) -> set:
        return {idx["name"] for idx in inspector.get_indexes(table)}

    def _drop_index(name: str, table: str):
        if name in _existing_indexes(table):
            op.drop_index(name, table)

    # Drop composite indexes
    _drop_index("ix_transactions_user_timestamp", "transactions")
    _drop_index("ix_alerts_user_status", "alerts")
    _drop_index("ix_alerts_status_severity", "alerts")

    # Drop case indexes
    _drop_index("ix_cases_assigned_to", "cases")
    _drop_index("ix_cases_priority", "cases")
    _drop_index("ix_cases_status", "cases")

    # Drop alert indexes
    _drop_index("ix_alerts_created_at", "alerts")
    _drop_index("ix_alerts_sar_filed", "alerts")
    _drop_index("ix_alerts_assigned_to", "alerts")
    _drop_index("ix_alerts_status", "alerts")
    _drop_index("ix_alerts_transaction_id", "alerts")

    # Drop transaction indexes
    _drop_index("ix_transactions_risk_level", "transactions")
    _drop_index("ix_transactions_country_code", "transactions")
