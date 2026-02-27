"""Replace obligation dedup unique index with partial unique index.

Revision ID: 20260227_fix_obligation_dedup_hash_unique
Revises: 20260227_add_missing_fk_indexes
Create Date: 2026-02-27 10:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260227_fix_obligation_dedup_hash_unique"
down_revision = "20260227_add_missing_fk_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    duplicate_row = bind.execute(
        sa.text(
            """
            SELECT doc_id, dedup_hash, COUNT(*) AS dup_count
            FROM regulatory_obligations
            WHERE dedup_hash IS NOT NULL
            GROUP BY doc_id, dedup_hash
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).fetchone()

    if duplicate_row is not None:
        raise RuntimeError(
            "Cannot apply partial unique dedup index: duplicate non-null dedup_hash rows exist "
            f"for doc_id={duplicate_row[0]}, dedup_hash={duplicate_row[1]}"
        )

    # Concurrent DDL must run outside transaction blocks.
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS uq_regulatory_obligations_doc_dedup_hash")
        op.execute(
            """
            CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_regulatory_obligations_doc_dedup_hash
            ON regulatory_obligations (doc_id, dedup_hash)
            WHERE dedup_hash IS NOT NULL
            """
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS uq_regulatory_obligations_doc_dedup_hash")
        op.execute(
            """
            CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_regulatory_obligations_doc_dedup_hash
            ON regulatory_obligations (doc_id, dedup_hash)
            """
        )
