"""Add policy_templates table

Revision ID: 4788ca423751
Revises: m7n8o9p2q3r4
Create Date: 2026-02-01
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4788ca423751"
down_revision = "m7n8o9p2q3r4"
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
        "policy_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("template_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=True),
        sa.Column("owner", sa.String(length=255), nullable=True),
        sa.Column("review_frequency_months", sa.Integer(), nullable=True),
        sa.Column("regulatory_basis", json_type, nullable=True),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("metadata", json_type, nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    op.create_index(
        "ix_policy_templates_template_id", "policy_templates", ["template_id"], unique=True
    )
    op.create_index("ix_policy_templates_category", "policy_templates", ["category"], unique=False)


def downgrade():
    op.drop_index("ix_policy_templates_category", table_name="policy_templates")
    op.drop_index("ix_policy_templates_template_id", table_name="policy_templates")
    op.drop_table("policy_templates")
