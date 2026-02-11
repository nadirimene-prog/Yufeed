"""add case_notes table

Revision ID: 20260211_case_notes
Revises: 20260211_evidence_packs
Create Date: 2026-02-11

Investigation notes attached to cases.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260211_case_notes"
down_revision = "20260211_evidence_packs"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "case_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column(
            "case_id",
            sa.Integer(),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("author_id", sa.String(length=255), nullable=False),
        sa.Column("author_email", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("note_type", sa.String(length=50), nullable=False, server_default="general"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_case_notes_case_id", "case_notes", ["case_id"])
    op.create_index("ix_case_notes_tenant_id", "case_notes", ["tenant_id"])


def downgrade():
    op.drop_index("ix_case_notes_tenant_id", table_name="case_notes")
    op.drop_index("ix_case_notes_case_id", table_name="case_notes")
    op.drop_table("case_notes")
