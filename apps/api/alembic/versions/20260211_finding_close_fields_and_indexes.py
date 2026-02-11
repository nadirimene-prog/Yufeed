"""add closed_reason and closed_comment to findings, plus composite indexes

Revision ID: 20260211_finding_close
Revises: 20260210_findings
Create Date: 2026-02-11

Adds close metadata columns and performance indexes for the findings table.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260211_finding_close"
down_revision = "20260210_findings"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("findings", sa.Column("closed_reason", sa.String(length=50), nullable=True))
    op.add_column("findings", sa.Column("closed_comment", sa.Text(), nullable=True))

    op.create_index(
        "ix_findings_tenant_status_created",
        "findings",
        ["tenant_id", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_findings_tenant_severity_status",
        "findings",
        ["tenant_id", "severity", "status"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_findings_tenant_severity_status", table_name="findings")
    op.drop_index("ix_findings_tenant_status_created", table_name="findings")
    op.drop_column("findings", "closed_comment")
    op.drop_column("findings", "closed_reason")
