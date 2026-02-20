"""Add dedup hash for regulatory obligations.

Revision ID: 20260220_obligation_dedup_hash
Revises: 20260220_supervisory_alerts
Create Date: 2026-02-20 12:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260220_obligation_dedup_hash"
down_revision = "20260220_supervisory_alerts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "regulatory_obligations",
        sa.Column("dedup_hash", sa.String(length=64), nullable=True),
    )
    op.create_index(
        op.f("ix_regulatory_obligations_dedup_hash"),
        "regulatory_obligations",
        ["dedup_hash"],
        unique=False,
    )
    op.create_index(
        "uq_regulatory_obligations_doc_dedup_hash",
        "regulatory_obligations",
        ["doc_id", "dedup_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_regulatory_obligations_doc_dedup_hash", table_name="regulatory_obligations")
    op.drop_index(op.f("ix_regulatory_obligations_dedup_hash"), table_name="regulatory_obligations")
    op.drop_column("regulatory_obligations", "dedup_hash")
