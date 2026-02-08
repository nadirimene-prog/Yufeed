"""add_rule_versions

Revision ID: 9f3c2b1a7d55
Revises: f2c0e7b9a1c5
Create Date: 2026-01-22 19:05:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "9f3c2b1a7d55"
down_revision: Union[str, Sequence[str], None] = "f2c0e7b9a1c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    json_type = postgresql.JSONB() if dialect == "postgresql" else sa.JSON()

    op.create_table(
        "rule_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rule_id", sa.Integer(), sa.ForeignKey("monitoring_rules.id"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("category", sa.String(100)),
        sa.Column("severity", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("conditions", json_type, nullable=False),
        sa.Column("thresholds", json_type),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", sa.String(255)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("approved_by", sa.String(255)),
        sa.Column("approved_at", sa.DateTime()),
        sa.Column("notes", sa.Text()),
    )

    op.create_index("ix_rule_versions_rule_id", "rule_versions", ["rule_id"])
    op.create_index("ix_rule_versions_status", "rule_versions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_rule_versions_status", table_name="rule_versions")
    op.drop_index("ix_rule_versions_rule_id", table_name="rule_versions")
    op.drop_table("rule_versions")
