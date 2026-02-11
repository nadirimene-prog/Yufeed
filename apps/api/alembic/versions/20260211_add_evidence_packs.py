"""add evidence_packs table

Revision ID: 20260211_evidence_packs
Revises: 20260211_case_decisions
Create Date: 2026-02-11

Stores versioned, hashed evidence snapshots for cases.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = "20260211_evidence_packs"
down_revision = "20260211_case_decisions"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "evidence_packs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pack_id", sa.String(length=64), unique=True, nullable=False, index=True),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column(
            "case_id",
            sa.Integer(),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("schema_version", sa.String(length=20), nullable=False, server_default="v1"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("format", sa.String(length=10), nullable=False, server_default="json"),
        sa.Column(
            "snapshot",
            sa.JSON().with_variant(JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column("integrity_hash", sa.String(length=64), nullable=False),
        sa.Column("storage_ref", sa.String(length=500), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_evidence_packs_case_id", "evidence_packs", ["case_id"])
    op.create_index("ix_evidence_packs_tenant_id", "evidence_packs", ["tenant_id"])


def downgrade():
    op.drop_index("ix_evidence_packs_tenant_id", table_name="evidence_packs")
    op.drop_index("ix_evidence_packs_case_id", table_name="evidence_packs")
    op.drop_table("evidence_packs")
