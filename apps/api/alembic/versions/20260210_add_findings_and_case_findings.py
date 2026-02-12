"""add findings table and case_findings association

Revision ID: 20260210_findings
Revises: 20260206_indexes
Create Date: 2026-02-10

Introduces the Finding-first workbench:
- findings: normalized signals for triage (alerts, obligation issues, etc.)
- case_findings: many-to-many link between cases and findings
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = "20260210_findings"
down_revision = "20260206_indexes"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "findings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(length=255), nullable=False, index=True),
        sa.Column("finding_type", sa.String(length=50), nullable=False, index=True),
        sa.Column("severity", sa.String(length=20), nullable=True, index=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="new", index=True),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("source_refs", sa.JSON().with_variant(JSONB(), "postgresql"), nullable=True),
        sa.Column("fingerprint", sa.String(length=128), nullable=False, index=True),
        sa.Column(
            "explainability",
            sa.JSON().with_variant(JSONB(), "postgresql"),
            nullable=True,
        ),
        sa.Column("assigned_to", sa.String(length=255), nullable=True, index=True),
        sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "fingerprint", name="uq_findings_tenant_fingerprint"),
    )

    op.create_index(
        "ix_findings_tenant_created_at",
        "findings",
        ["tenant_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "case_findings",
        sa.Column(
            "case_id",
            sa.Integer(),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "finding_id",
            sa.Integer(),
            sa.ForeignKey("findings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint("case_id", "finding_id", name="uq_case_findings_case_finding"),
    )
    op.create_index("ix_case_findings_case_id", "case_findings", ["case_id"], unique=False)
    op.create_index("ix_case_findings_finding_id", "case_findings", ["finding_id"], unique=False)


def downgrade():
    op.drop_index("ix_case_findings_finding_id", table_name="case_findings")
    op.drop_index("ix_case_findings_case_id", table_name="case_findings")
    op.drop_table("case_findings")

    op.drop_index("ix_findings_tenant_created_at", table_name="findings")
    op.drop_table("findings")
