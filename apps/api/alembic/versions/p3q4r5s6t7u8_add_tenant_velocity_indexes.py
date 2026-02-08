"""Add tenant-scoped velocity indexes for transaction feature computation.

Revision ID: p3q4r5s6t7u8
Revises: p2q3r4s5t6u7
Create Date: 2026-02-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "p3q4r5s6t7u8"
down_revision: Union[str, Sequence[str], None] = "p2q3r4s5t6u7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TX_TENANT_USER_TIME_INDEX = "ix_transactions_tenant_user_timestamp"
TX_TENANT_TIME_INDEX = "ix_transactions_tenant_timestamp"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "transactions" not in inspector.get_table_names():
        return

    indexes = {idx["name"] for idx in inspector.get_indexes("transactions")}

    if TX_TENANT_USER_TIME_INDEX not in indexes:
        op.create_index(
            TX_TENANT_USER_TIME_INDEX,
            "transactions",
            ["tenant_id", "user_id", "timestamp"],
            unique=False,
        )

    if TX_TENANT_TIME_INDEX not in indexes:
        op.create_index(
            TX_TENANT_TIME_INDEX,
            "transactions",
            ["tenant_id", "timestamp"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "transactions" not in inspector.get_table_names():
        return

    indexes = {idx["name"] for idx in inspector.get_indexes("transactions")}

    if TX_TENANT_TIME_INDEX in indexes:
        op.drop_index(TX_TENANT_TIME_INDEX, table_name="transactions")

    if TX_TENANT_USER_TIME_INDEX in indexes:
        op.drop_index(TX_TENANT_USER_TIME_INDEX, table_name="transactions")
