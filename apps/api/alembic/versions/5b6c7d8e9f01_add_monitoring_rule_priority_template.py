"""add monitoring rule priority/template columns

Revision ID: 5b6c7d8e9f01
Revises: 4d7e8f9a5b67
Create Date: 2026-01-23 11:05:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5b6c7d8e9f01"
down_revision = "4d7e8f9a5b67"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "monitoring_rules" not in inspector.get_table_names():
        return

    existing_columns = {col["name"] for col in inspector.get_columns("monitoring_rules")}
    added_priority = False
    added_template = False

    if "priority" not in existing_columns:
        op.add_column(
            "monitoring_rules",
            sa.Column("priority", sa.Integer(), nullable=False, server_default="3"),
        )
        added_priority = True

    if "is_template" not in existing_columns:
        op.add_column(
            "monitoring_rules",
            sa.Column("is_template", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )
        added_template = True

    if bind.dialect.name != "sqlite":
        if added_priority:
            op.alter_column("monitoring_rules", "priority", server_default=None)

        if added_template:
            op.alter_column("monitoring_rules", "is_template", server_default=None)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "monitoring_rules" not in inspector.get_table_names():
        return

    existing_columns = {col["name"] for col in inspector.get_columns("monitoring_rules")}

    if "is_template" in existing_columns:
        op.drop_column("monitoring_rules", "is_template")

    if "priority" in existing_columns:
        op.drop_column("monitoring_rules", "priority")
