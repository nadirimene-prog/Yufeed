"""Add failed_transaction_processing_items table for transaction DLQ.

Revision ID: p4q5r6s7t8u9
Revises: p3q4r5s6t7u8
Create Date: 2026-02-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "p4q5r6s7t8u9"
down_revision: Union[str, Sequence[str], None] = "p3q4r5s6t7u8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "failed_transaction_processing_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("transaction_db_id", sa.Integer(), nullable=False),
        sa.Column("transaction_id", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_traceback", sa.Text(), nullable=True),
        sa.Column(
            "payload_json",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column("retry_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=True, server_default="3"),
        sa.Column("status", sa.String(length=50), nullable=True, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("last_retry_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_failed_tx_processing_tenant_id",
        "failed_transaction_processing_items",
        ["tenant_id"],
    )
    op.create_index(
        "ix_failed_tx_processing_transaction_db_id",
        "failed_transaction_processing_items",
        ["transaction_db_id"],
    )
    op.create_index(
        "ix_failed_tx_processing_status",
        "failed_transaction_processing_items",
        ["status"],
    )
    op.create_index(
        "ix_failed_tx_processing_created_at",
        "failed_transaction_processing_items",
        ["created_at"],
    )
    op.create_index(
        "ix_failed_tx_processing_retry_lookup",
        "failed_transaction_processing_items",
        ["status", "retry_count", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_failed_tx_processing_retry_lookup", table_name="failed_transaction_processing_items"
    )
    op.drop_index(
        "ix_failed_tx_processing_created_at", table_name="failed_transaction_processing_items"
    )
    op.drop_index(
        "ix_failed_tx_processing_status", table_name="failed_transaction_processing_items"
    )
    op.drop_index(
        "ix_failed_tx_processing_transaction_db_id",
        table_name="failed_transaction_processing_items",
    )
    op.drop_index(
        "ix_failed_tx_processing_tenant_id", table_name="failed_transaction_processing_items"
    )
    op.drop_table("failed_transaction_processing_items")
