"""Add failed_ingestion_items table for DLQ

Revision ID: n8o9p0q1r2s3
Revises: af3b7e9d1cb5
Create Date: 2026-02-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "n8o9p0q1r2s3"
down_revision: Union[str, Sequence[str], None] = "af3b7e9d1cb5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create failed_ingestion_items table for Dead Letter Queue."""
    op.create_table(
        "failed_ingestion_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("celex", sa.String(64), nullable=True),
        sa.Column("source_key", sa.String(255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_traceback", sa.Text(), nullable=True),
        sa.Column(
            "entry_json",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column("retry_count", sa.Integer(), nullable=True, default=0),
        sa.Column("max_retries", sa.Integer(), nullable=True, default=3),
        sa.Column("status", sa.String(50), nullable=True, default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("last_retry_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_doc_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["resolved_doc_id"],
            ["legal_documents.id"],
            name="fk_failed_ingestion_resolved_doc",
        ),
    )

    # Create indexes for common queries
    op.create_index(
        "ix_failed_ingestion_items_celex",
        "failed_ingestion_items",
        ["celex"],
    )
    op.create_index(
        "ix_failed_ingestion_items_source_key",
        "failed_ingestion_items",
        ["source_key"],
    )
    op.create_index(
        "ix_failed_ingestion_items_status",
        "failed_ingestion_items",
        ["status"],
    )
    op.create_index(
        "ix_failed_ingestion_items_created_at",
        "failed_ingestion_items",
        ["created_at"],
    )
    # Composite index for retry queries
    op.create_index(
        "ix_failed_ingestion_items_retry_lookup",
        "failed_ingestion_items",
        ["status", "retry_count", "created_at"],
    )


def downgrade() -> None:
    """Drop failed_ingestion_items table."""
    op.drop_index("ix_failed_ingestion_items_retry_lookup", table_name="failed_ingestion_items")
    op.drop_index("ix_failed_ingestion_items_created_at", table_name="failed_ingestion_items")
    op.drop_index("ix_failed_ingestion_items_status", table_name="failed_ingestion_items")
    op.drop_index("ix_failed_ingestion_items_source_key", table_name="failed_ingestion_items")
    op.drop_index("ix_failed_ingestion_items_celex", table_name="failed_ingestion_items")
    op.drop_table("failed_ingestion_items")
