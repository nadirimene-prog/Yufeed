"""Add tenant composite uniques for transaction monitoring tables.

Revision ID: p1q2r3s4t5u6
Revises: p0q1r2s3t4u5
Create Date: 2026-02-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "p1q2r3s4t5u6"
down_revision: Union[str, Sequence[str], None] = "p0q1r2s3t4u5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TX_TENANT_UNIQUE = "uq_transactions_tenant_transaction_id"
USER_RISK_TENANT_UNIQUE = "uq_user_risk_profiles_tenant_user_id"


def _drop_single_column_unique(inspector: sa.Inspector, table: str, column: str) -> None:
    for uc in inspector.get_unique_constraints(table):
        cols = uc.get("column_names") or []
        if cols == [column]:
            name = uc.get("name")
            if name:
                op.drop_constraint(name, table, type_="unique")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "transactions" in tables:
        _drop_single_column_unique(inspector, "transactions", "transaction_id")

        unique_constraints = {c["name"] for c in inspector.get_unique_constraints("transactions")}
        if TX_TENANT_UNIQUE not in unique_constraints:
            op.create_unique_constraint(
                TX_TENANT_UNIQUE,
                "transactions",
                ["tenant_id", "transaction_id"],
            )

    if "user_risk_profiles" in tables:
        _drop_single_column_unique(inspector, "user_risk_profiles", "user_id")

        unique_constraints = {c["name"] for c in inspector.get_unique_constraints("user_risk_profiles")}
        if USER_RISK_TENANT_UNIQUE not in unique_constraints:
            op.create_unique_constraint(
                USER_RISK_TENANT_UNIQUE,
                "user_risk_profiles",
                ["tenant_id", "user_id"],
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "transactions" in tables:
        unique_constraints = {c["name"] for c in inspector.get_unique_constraints("transactions")}
        if TX_TENANT_UNIQUE in unique_constraints:
            op.drop_constraint(TX_TENANT_UNIQUE, "transactions", type_="unique")

        op.create_unique_constraint(
            "uq_transactions_transaction_id",
            "transactions",
            ["transaction_id"],
        )

    if "user_risk_profiles" in tables:
        unique_constraints = {c["name"] for c in inspector.get_unique_constraints("user_risk_profiles")}
        if USER_RISK_TENANT_UNIQUE in unique_constraints:
            op.drop_constraint(USER_RISK_TENANT_UNIQUE, "user_risk_profiles", type_="unique")

        op.create_unique_constraint(
            "uq_user_risk_profiles_user_id",
            "user_risk_profiles",
            ["user_id"],
        )

