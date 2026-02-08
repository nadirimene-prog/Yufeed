"""Add tenant_id to audit/event/decision immutable tables.

Revision ID: p2q3r4s5t6u7
Revises: p1q2r3s4t5u6
Create Date: 2026-02-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "p2q3r4s5t6u7"
down_revision: Union[str, Sequence[str], None] = "p1q2r3s4t5u6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLES = (
    ("audit_logs", "ix_audit_logs_tenant_created_at"),
    ("event_records", "ix_event_records_tenant_created_at"),
    ("decision_records", "ix_decision_records_tenant_created_at"),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    dialect = bind.dialect.name

    for table_name, index_name in TABLES:
        if table_name not in tables:
            continue

        columns = {c["name"] for c in inspector.get_columns(table_name)}
        if "tenant_id" not in columns:
            op.add_column(
                table_name,
                sa.Column(
                    "tenant_id", sa.String(length=255), nullable=False, server_default="default"
                ),
            )

        existing_indexes = {i["name"] for i in inspector.get_indexes(table_name)}
        if index_name not in existing_indexes and "created_at" in columns:
            op.create_index(index_name, table_name, ["tenant_id", "created_at"], unique=False)

        # Remove default for new inserts (Postgres/MySQL). SQLite alters require table rebuild, skip.
        if dialect != "sqlite":
            op.alter_column(table_name, "tenant_id", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    for table_name, index_name in TABLES:
        if table_name not in tables:
            continue

        existing_indexes = {i["name"] for i in inspector.get_indexes(table_name)}
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name=table_name)

        columns = {c["name"] for c in inspector.get_columns(table_name)}
        if "tenant_id" in columns:
            op.drop_column(table_name, "tenant_id")
