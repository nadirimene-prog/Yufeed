"""Add JSONB GIN indexes for containment queries.

Revision ID: 20260227_add_jsonb_gin_indexes
Revises: 20260227_fix_obligation_dedup_hash_unique
Create Date: 2026-02-27 12:00:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260227_add_jsonb_gin_indexes"
down_revision = "20260227_fix_obligation_dedup_hash_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_legal_documents_scope_tags_gin
            ON legal_documents USING gin ((scope_tags::jsonb) jsonb_path_ops)
            """
        )
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_supervisory_alerts_topics_gin
            ON supervisory_alerts USING gin ((topics::jsonb) jsonb_path_ops)
            """
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_supervisory_alerts_topics_gin")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_legal_documents_scope_tags_gin")
