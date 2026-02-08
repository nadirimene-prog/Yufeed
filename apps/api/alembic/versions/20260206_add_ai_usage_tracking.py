"""add ai usage tracking tables

Revision ID: 20260206_ai_usage
Revises: (previous_revision)
Create Date: 2026-02-06

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = "20260206_ai_usage"
down_revision = "p4q5r6s7t8u9"  # Latest revision (DLQ table)
branch_labels = None
depends_on = None


def upgrade():
    # Create ai_usage_logs table
    op.create_table(
        "ai_usage_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("operation", sa.String(100), nullable=True),
        sa.Column("document_id", sa.Integer(), nullable=True),
        sa.Column("obligation_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.String(255), nullable=True),
        sa.Column("request_metadata", JSONB, nullable=True),
        sa.Column("response_metadata", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["document_id"], ["legal_documents.id"]),
        sa.ForeignKeyConstraint(["obligation_id"], ["regulatory_obligations.id"]),
    )

    # Indexes for ai_usage_logs
    op.create_index("idx_ai_usage_tenant_created", "ai_usage_logs", ["tenant_id", "created_at"])
    op.create_index("idx_ai_usage_provider_model", "ai_usage_logs", ["provider", "model"])
    op.create_index("idx_ai_usage_operation", "ai_usage_logs", ["operation"])
    op.create_index("ix_ai_usage_logs_tenant_id", "ai_usage_logs", ["tenant_id"])
    op.create_index("ix_ai_usage_logs_created_at", "ai_usage_logs", ["created_at"])

    # Create ai_budgets table
    op.create_table(
        "ai_budgets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("daily_limit_usd", sa.Float(), nullable=False, server_default="100.0"),
        sa.Column("monthly_limit_usd", sa.Float(), nullable=False, server_default="3000.0"),
        sa.Column("daily_usage_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("monthly_usage_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("daily_reset_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("monthly_reset_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("warning_threshold_percent", sa.Integer(), server_default="80"),
        sa.Column("critical_threshold_percent", sa.Integer(), server_default="95"),
        sa.Column("daily_warning_sent", sa.DateTime(timezone=True), nullable=True),
        sa.Column("daily_critical_sent", sa.DateTime(timezone=True), nullable=True),
        sa.Column("monthly_warning_sent", sa.DateTime(timezone=True), nullable=True),
        sa.Column("monthly_critical_sent", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.UniqueConstraint("tenant_id"),
    )


def downgrade():
    op.drop_table("ai_budgets")

    op.drop_index("ix_ai_usage_logs_created_at", "ai_usage_logs")
    op.drop_index("ix_ai_usage_logs_tenant_id", "ai_usage_logs")
    op.drop_index("idx_ai_usage_operation", "ai_usage_logs")
    op.drop_index("idx_ai_usage_provider_model", "ai_usage_logs")
    op.drop_index("idx_ai_usage_tenant_created", "ai_usage_logs")

    op.drop_table("ai_usage_logs")
