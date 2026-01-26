"""add regulatory sources and compliance workflow tables

Revision ID: 6c9d1a2b3c4d
Revises: 5b6c7d8e9f01
Create Date: 2026-01-23 12:15:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "6c9d1a2b3c4d"
down_revision = "5b6c7d8e9f01"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    json_type = postgresql.JSONB(astext_type=sa.Text()) if bind.dialect.name == "postgresql" else sa.JSON()

    # Add source metadata to legal_documents
    existing_columns = {col["name"] for col in inspector.get_columns("legal_documents")}
    if "source_system" not in existing_columns:
        op.add_column("legal_documents", sa.Column("source_system", sa.String(), nullable=True))
    if "source_reference" not in existing_columns:
        op.add_column("legal_documents", sa.Column("source_reference", sa.String(), nullable=True))
    if "jurisdiction" not in existing_columns:
        op.add_column("legal_documents", sa.Column("jurisdiction", sa.String(), nullable=True))
    if "primary_language" not in existing_columns:
        op.add_column(
            "legal_documents",
            sa.Column("primary_language", sa.String(), nullable=False, server_default="en"),
        )
        if bind.dialect.name != "sqlite":
            op.alter_column("legal_documents", "primary_language", server_default=None)

    # Regulatory sources
    op.create_table(
        "regulatory_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_key", sa.String(length=255), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("jurisdiction", sa.String(length=100), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("source_type", sa.String(length=50), nullable=False, server_default="rss"),
        sa.Column("base_url", sa.String(length=1000), nullable=True),
        sa.Column("schedule", sa.String(length=50), nullable=True, server_default="daily"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_ingested_at", sa.DateTime(), nullable=True),
        sa.Column("metadata", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True, onupdate=sa.func.now()),
    )
    op.create_index("ix_regulatory_sources_source_key", "regulatory_sources", ["source_key"], unique=True)

    # Ingestion runs
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("regulatory_sources.id"), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="running"),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("items_seen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_new", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors", json_type, nullable=True),
    )
    op.create_index("ix_ingestion_runs_source_id", "ingestion_runs", ["source_id"], unique=False)

    # Language-specific document texts
    op.create_table(
        "legal_document_texts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("doc_id", sa.Integer(), sa.ForeignKey("legal_documents.id"), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("full_text", sa.Text(), nullable=True),
        sa.Column("article_breakdown", json_type, nullable=True),
        sa.Column("content_extraction_method", sa.String(length=50), nullable=True),
        sa.Column("content_extracted_at", sa.DateTime(), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=True),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True, onupdate=sa.func.now()),
    )
    op.create_index("ix_legal_document_texts_doc_language", "legal_document_texts", ["doc_id", "language"], unique=True)

    # Regulatory obligations
    op.create_table(
        "regulatory_obligations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("obligation_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("doc_id", sa.Integer(), sa.ForeignKey("legal_documents.id"), nullable=False),
        sa.Column("celex", sa.String(length=64), nullable=True),
        sa.Column("article_ref", sa.String(length=255), nullable=True),
        sa.Column("obligation_text", sa.Text(), nullable=False),
        sa.Column("applicability", sa.Text(), nullable=True),
        sa.Column("effective_date", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("reviewed_by", sa.String(length=255), nullable=True),
        sa.Column("approved_by", sa.String(length=255), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("tags", json_type, nullable=True),
        sa.Column("evidence", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True, onupdate=sa.func.now()),
    )
    op.create_index("ix_regulatory_obligations_obligation_id", "regulatory_obligations", ["obligation_id"], unique=True)
    op.create_index("ix_regulatory_obligations_doc_id", "regulatory_obligations", ["doc_id"], unique=False)

    # Policy documents
    op.create_table(
        "policy_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("policy_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=True),
        sa.Column("owner", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("effective_date", sa.DateTime(), nullable=True),
        sa.Column("last_reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("metadata", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True, onupdate=sa.func.now()),
    )
    op.create_index("ix_policy_documents_policy_id", "policy_documents", ["policy_id"], unique=True)

    # Policy sections
    op.create_table(
        "policy_sections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("policy_id", sa.Integer(), sa.ForeignKey("policy_documents.id"), nullable=False),
        sa.Column("section_ref", sa.String(length=100), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("version", sa.String(length=50), nullable=True),
        sa.Column("last_reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True, onupdate=sa.func.now()),
    )
    op.create_index("ix_policy_sections_policy_id", "policy_sections", ["policy_id"], unique=False)

    # Internal rules
    op.create_table(
        "internal_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("internal_rule_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("obligation_id", sa.Integer(), sa.ForeignKey("regulatory_obligations.id"), nullable=False),
        sa.Column("policy_section_id", sa.Integer(), sa.ForeignKey("policy_sections.id"), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("control_owner", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("reviewed_by", sa.String(length=255), nullable=True),
        sa.Column("approved_by", sa.String(length=255), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True, onupdate=sa.func.now()),
    )
    op.create_index("ix_internal_rules_internal_rule_id", "internal_rules", ["internal_rule_id"], unique=True)
    op.create_index("ix_internal_rules_obligation_id", "internal_rules", ["obligation_id"], unique=False)

    # Internal rule mappings to monitoring rules
    op.create_table(
        "internal_rule_mappings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("internal_rule_id", sa.Integer(), sa.ForeignKey("internal_rules.id"), nullable=False),
        sa.Column("monitoring_rule_id", sa.Integer(), sa.ForeignKey("monitoring_rules.id"), nullable=True),
        sa.Column("mapping_type", sa.String(length=50), nullable=False, server_default="transaction_monitoring"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_internal_rule_mappings_internal_rule_id", "internal_rule_mappings", ["internal_rule_id"], unique=False)
    op.create_index("ix_internal_rule_mappings_monitoring_rule_id", "internal_rule_mappings", ["monitoring_rule_id"], unique=False)


def downgrade():
    op.drop_index("ix_internal_rule_mappings_monitoring_rule_id", table_name="internal_rule_mappings")
    op.drop_index("ix_internal_rule_mappings_internal_rule_id", table_name="internal_rule_mappings")
    op.drop_table("internal_rule_mappings")

    op.drop_index("ix_internal_rules_obligation_id", table_name="internal_rules")
    op.drop_index("ix_internal_rules_internal_rule_id", table_name="internal_rules")
    op.drop_table("internal_rules")

    op.drop_index("ix_policy_sections_policy_id", table_name="policy_sections")
    op.drop_table("policy_sections")

    op.drop_index("ix_policy_documents_policy_id", table_name="policy_documents")
    op.drop_table("policy_documents")

    op.drop_index("ix_regulatory_obligations_doc_id", table_name="regulatory_obligations")
    op.drop_index("ix_regulatory_obligations_obligation_id", table_name="regulatory_obligations")
    op.drop_table("regulatory_obligations")

    op.drop_index("ix_legal_document_texts_doc_language", table_name="legal_document_texts")
    op.drop_table("legal_document_texts")

    op.drop_index("ix_ingestion_runs_source_id", table_name="ingestion_runs")
    op.drop_table("ingestion_runs")

    op.drop_index("ix_regulatory_sources_source_key", table_name="regulatory_sources")
    op.drop_table("regulatory_sources")

    op.drop_column("legal_documents", "primary_language")
    op.drop_column("legal_documents", "jurisdiction")
    op.drop_column("legal_documents", "source_reference")
    op.drop_column("legal_documents", "source_system")
