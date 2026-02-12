"""add case_decisions table

Revision ID: 20260211_case_decisions
Revises: 20260211_finding_close
Create Date: 2026-02-11

Introduces the governance decision workflow for investigation cases.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = "20260211_case_decisions"
down_revision = "20260211_finding_close"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "case_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(length=255), nullable=False, index=True),
        sa.Column(
            "case_id",
            sa.Integer(),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("disposition", sa.String(length=50), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approver_id", sa.String(length=255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_case_decisions_case_id", "case_decisions", ["case_id"])
    op.create_index("ix_case_decisions_tenant_status", "case_decisions", ["tenant_id", "status"])


def downgrade():
    op.drop_index("ix_case_decisions_tenant_status", table_name="case_decisions")
    op.drop_index("ix_case_decisions_case_id", table_name="case_decisions")
    op.drop_table("case_decisions")
