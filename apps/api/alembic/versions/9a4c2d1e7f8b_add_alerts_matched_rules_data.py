"""add matched_rules_data to alerts

Revision ID: 9a4c2d1e7f8b
Revises: 8f2d9a1c4e6b
Create Date: 2026-01-24 23:40:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "9a4c2d1e7f8b"
down_revision: Union[str, Sequence[str], None] = "8f2d9a1c4e6b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("alerts")}
    json_type = postgresql.JSONB(astext_type=sa.Text()) if bind.dialect.name == "postgresql" else sa.JSON()

    if "matched_rules_data" not in columns:
        op.add_column("alerts", sa.Column("matched_rules_data", json_type, nullable=True))

    if "matched_rules" in columns:
        op.execute(
            "UPDATE alerts SET matched_rules_data = matched_rules "
            "WHERE matched_rules_data IS NULL"
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {col["name"] for col in inspector.get_columns("alerts")}
    if "matched_rules_data" in columns:
        op.drop_column("alerts", "matched_rules_data")
