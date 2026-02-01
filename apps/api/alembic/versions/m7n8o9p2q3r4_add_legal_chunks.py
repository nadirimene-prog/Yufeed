"""Add legal_chunks table

Revision ID: m7n8o9p2q3r4
Revises: l6m7n8o9p1
Create Date: 2026-01-31
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "m7n8o9p2q3r4"
down_revision = "h2i3j4k5l6m7"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import JSONB
        json_type = JSONB
    else:
        json_type = sa.JSON

    op.create_table(
        "legal_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("chunk_id", sa.String(length=255), nullable=False),
        sa.Column("doc_id", sa.Integer(), sa.ForeignKey("legal_documents.id"), nullable=False),
        sa.Column("celex", sa.String(), nullable=False),
        sa.Column("source_system", sa.String(), nullable=True),
        sa.Column("jurisdiction", sa.String(), nullable=True),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column("section_title", sa.Text(), nullable=True),
        sa.Column("article_ref", sa.String(length=100), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("char_count", sa.Integer(), nullable=True),
        sa.Column("metadata", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )

    op.create_index("ix_legal_chunks_chunk_id", "legal_chunks", ["chunk_id"], unique=True)
    op.create_index("ix_legal_chunks_doc_id", "legal_chunks", ["doc_id"])
    op.create_index("ix_legal_chunks_celex", "legal_chunks", ["celex"])
    op.create_index("ix_legal_chunks_created_at", "legal_chunks", ["created_at"])


def downgrade():
    op.drop_index("ix_legal_chunks_created_at", table_name="legal_chunks")
    op.drop_index("ix_legal_chunks_celex", table_name="legal_chunks")
    op.drop_index("ix_legal_chunks_doc_id", table_name="legal_chunks")
    op.drop_index("ix_legal_chunks_chunk_id", table_name="legal_chunks")
    op.drop_table("legal_chunks")
