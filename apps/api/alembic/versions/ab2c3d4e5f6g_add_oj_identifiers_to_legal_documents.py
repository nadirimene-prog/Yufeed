"""add OJ act identifiers to legal documents

Revision ID: ab2c3d4e5f6g
Revises: aa1b2c3d4e5f
Create Date: 2026-01-25 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "ab2c3d4e5f6g"
down_revision = "aa1b2c3d4e5f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("legal_documents", sa.Column("oj_act_identifier", sa.String(), nullable=True))
    op.add_column("legal_documents", sa.Column("oj_signature_identifier", sa.String(), nullable=True))
    op.create_index(
        "ix_legal_documents_oj_act_identifier",
        "legal_documents",
        ["oj_act_identifier"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_legal_documents_oj_act_identifier", table_name="legal_documents")
    op.drop_column("legal_documents", "oj_signature_identifier")
    op.drop_column("legal_documents", "oj_act_identifier")
