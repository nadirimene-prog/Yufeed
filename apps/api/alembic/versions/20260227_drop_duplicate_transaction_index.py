"""Drop duplicate transaction index name after ensuring canonical index exists.

Revision ID: 20260227_drop_dup_txn_idx
Revises: 20260227_add_jsonb_gin_indexes
Create Date: 2026-02-27 12:10:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260227_drop_dup_txn_idx"
down_revision = "20260227_add_jsonb_gin_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_transactions_tenant_user_timestamp
            ON transactions (tenant_id, user_id, timestamp)
            """
        )
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_txn_tenant_user_timestamp")


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_txn_tenant_user_timestamp
            ON transactions (tenant_id, user_id, timestamp)
            """
        )
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_transactions_tenant_user_timestamp")
