"""Drop redundant ai_usage single-column indexes.

Revision ID: 20260227_drop_redundant_ai_usage_indexes
Revises: 20260227_drop_duplicate_transaction_index
Create Date: 2026-02-27 12:20:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260227_drop_redundant_ai_usage_indexes"
down_revision = "20260227_drop_duplicate_transaction_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        # Ensure the composite hot-path index exists before dropping redundant singles.
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ai_usage_tenant_created
            ON ai_usage_logs (tenant_id, created_at)
            """
        )
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_ai_usage_logs_tenant_id")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_ai_usage_logs_created_at")


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ai_usage_logs_tenant_id
            ON ai_usage_logs (tenant_id)
            """
        )
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ai_usage_logs_created_at
            ON ai_usage_logs (created_at)
            """
        )
