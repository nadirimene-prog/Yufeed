"""Add missing FK and composite indexes for hot paths.

Revision ID: 20260227_add_missing_fk_indexes
Revises: 20260220_obligation_dedup_hash
Create Date: 2026-02-27 10:00:00.000000
"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "20260227_add_missing_fk_indexes"
down_revision = "20260220_obligation_dedup_hash"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL requires autocommit for CONCURRENTLY operations.
    with op.get_context().autocommit_block():
        bind = op.get_bind()
        index_specs = (
            (
                "legal_versions",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_legal_versions_doc_id "
                "ON legal_versions (doc_id)",
            ),
            (
                "legal_relations",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_legal_relations_from_doc_id "
                "ON legal_relations (from_doc_id)",
            ),
            (
                "legal_relations",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_legal_relations_to_doc_id "
                "ON legal_relations (to_doc_id)",
            ),
            (
                "annotations",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_annotations_doc_id "
                "ON annotations (doc_id)",
            ),
            (
                "rule_hits",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_rule_hits_alert_id "
                "ON rule_hits (alert_id)",
            ),
            (
                "rule_hits",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_rule_hits_rule_id "
                "ON rule_hits (rule_id)",
            ),
            (
                "ingestion_runs",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ingestion_runs_source_id "
                "ON ingestion_runs (source_id)",
            ),
            (
                "legal_chunks",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_legal_chunks_doc_chunk_order "
                "ON legal_chunks (doc_id, chunk_index)",
            ),
            (
                "legal_chunks",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_legal_chunks_celex_language "
                "ON legal_chunks (celex, language)",
            ),
            (
                "tenant_audit_logs",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_tenant_audit_logs_tenant_created "
                "ON tenant_audit_logs (tenant_id, created_at)",
            ),
            (
                "compliance_profiles",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_compliance_profiles_tenant_status "
                "ON compliance_profiles (tenant_id, status)",
            ),
            (
                "user_risk_profiles",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_user_risk_tenant_risk_level "
                "ON user_risk_profiles (tenant_id, risk_level)",
            ),
        )

        for table_name, ddl in index_specs:
            table_regclass = bind.execute(
                sa.text("SELECT to_regclass(:table_name)"),
                {"table_name": f"public.{table_name}"},
            ).scalar_one()
            if table_regclass is not None:
                op.execute(ddl)


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_user_risk_tenant_risk_level")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_compliance_profiles_tenant_status")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_tenant_audit_logs_tenant_created")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_legal_chunks_celex_language")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_legal_chunks_doc_chunk_order")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_ingestion_runs_source_id")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_rule_hits_rule_id")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_rule_hits_alert_id")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_annotations_doc_id")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_legal_relations_to_doc_id")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_legal_relations_from_doc_id")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_legal_versions_doc_id")
