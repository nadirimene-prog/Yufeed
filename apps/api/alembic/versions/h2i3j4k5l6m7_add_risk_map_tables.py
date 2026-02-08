"""add risk map tables and linked_policy_id to obligations

Revision ID: h2i3j4k5l6m7
Revises: g1h2i3j4k5l6
Create Date: 2026-01-28 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "h2i3j4k5l6m7"
down_revision = "g1h2i3j4k5l6"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    json_type = (
        postgresql.JSONB(astext_type=sa.Text()) if bind.dialect.name == "postgresql" else sa.JSON()
    )

    # Add linked_policy_id to regulatory_obligations if it doesn't exist
    existing_columns = {col["name"] for col in inspector.get_columns("regulatory_obligations")}
    if "linked_policy_id" not in existing_columns:
        op.add_column(
            "regulatory_obligations",
            sa.Column(
                "linked_policy_id",
                sa.Integer(),
                sa.ForeignKey("policy_documents.id"),
                nullable=True,
            ),
        )
        op.create_index(
            "ix_regulatory_obligations_linked_policy_id",
            "regulatory_obligations",
            ["linked_policy_id"],
        )

    # Risk categories table
    op.create_table(
        "risk_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("risk_categories.id"), nullable=True),
        sa.Column("risk_level", sa.String(length=50), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True, onupdate=sa.func.now()),
    )
    op.create_index(
        "ix_risk_categories_category_id", "risk_categories", ["category_id"], unique=True
    )
    op.create_index("ix_risk_categories_parent_id", "risk_categories", ["parent_id"])

    # Risk entries table
    op.create_table(
        "risk_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("risk_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("risk_categories.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "inherent_risk_level", sa.String(length=50), nullable=False, server_default="medium"
        ),
        sa.Column(
            "residual_risk_level", sa.String(length=50), nullable=False, server_default="medium"
        ),
        sa.Column("likelihood", sa.String(length=50), nullable=True),
        sa.Column("impact", sa.String(length=50), nullable=True),
        sa.Column(
            "mitigation_status", sa.String(length=50), nullable=False, server_default="not_started"
        ),
        sa.Column("control_owner", sa.String(length=255), nullable=True),
        sa.Column("review_date", sa.DateTime(), nullable=True),
        sa.Column("metadata", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True, onupdate=sa.func.now()),
    )
    op.create_index("ix_risk_entries_risk_id", "risk_entries", ["risk_id"], unique=True)
    op.create_index("ix_risk_entries_category_id", "risk_entries", ["category_id"])

    # Obligation-Risk link table
    op.create_table(
        "obligation_risk_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "obligation_id",
            sa.Integer(),
            sa.ForeignKey("regulatory_obligations.id"),
            nullable=False,
        ),
        sa.Column("risk_entry_id", sa.Integer(), sa.ForeignKey("risk_entries.id"), nullable=False),
        sa.Column("link_type", sa.String(length=50), nullable=False, server_default="mitigates"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_obligation_risk_links_obligation_id", "obligation_risk_links", ["obligation_id"]
    )
    op.create_index(
        "ix_obligation_risk_links_risk_entry_id", "obligation_risk_links", ["risk_entry_id"]
    )

    # Seed default risk categories
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            INSERT INTO risk_categories (category_id, name, description, risk_level, status, created_at)
            VALUES
                ('RISK-CAT-001', 'Regulatory Risk', 'Non-compliance with laws and regulations', 'high', 'active', NOW()),
                ('RISK-CAT-002', 'Operational Risk', 'Process and system failures', 'medium', 'active', NOW()),
                ('RISK-CAT-003', 'Financial Risk', 'Financial losses and exposure', 'high', 'active', NOW()),
                ('RISK-CAT-004', 'Reputational Risk', 'Brand and trust damage', 'medium', 'active', NOW()),
                ('RISK-CAT-005', 'AML/CFT Risk', 'Money laundering and terrorist financing', 'critical', 'active', NOW()),
                ('RISK-CAT-006', 'Technology Risk', 'IT and cyber security risks', 'high', 'active', NOW()),
                ('RISK-CAT-007', 'Third-Party Risk', 'Vendor and partner risks', 'medium', 'active', NOW())
            ON CONFLICT (category_id) DO NOTHING;
        """
        )
    else:
        # SQLite compatible insert
        op.execute(
            """
            INSERT OR IGNORE INTO risk_categories (category_id, name, description, risk_level, status, created_at)
            VALUES
                ('RISK-CAT-001', 'Regulatory Risk', 'Non-compliance with laws and regulations', 'high', 'active', datetime('now')),
                ('RISK-CAT-002', 'Operational Risk', 'Process and system failures', 'medium', 'active', datetime('now')),
                ('RISK-CAT-003', 'Financial Risk', 'Financial losses and exposure', 'high', 'active', datetime('now')),
                ('RISK-CAT-004', 'Reputational Risk', 'Brand and trust damage', 'medium', 'active', datetime('now')),
                ('RISK-CAT-005', 'AML/CFT Risk', 'Money laundering and terrorist financing', 'critical', 'active', datetime('now')),
                ('RISK-CAT-006', 'Technology Risk', 'IT and cyber security risks', 'high', 'active', datetime('now')),
                ('RISK-CAT-007', 'Third-Party Risk', 'Vendor and partner risks', 'medium', 'active', datetime('now'));
        """
        )


def downgrade():
    op.drop_index("ix_obligation_risk_links_risk_entry_id", table_name="obligation_risk_links")
    op.drop_index("ix_obligation_risk_links_obligation_id", table_name="obligation_risk_links")
    op.drop_table("obligation_risk_links")

    op.drop_index("ix_risk_entries_category_id", table_name="risk_entries")
    op.drop_index("ix_risk_entries_risk_id", table_name="risk_entries")
    op.drop_table("risk_entries")

    op.drop_index("ix_risk_categories_parent_id", table_name="risk_categories")
    op.drop_index("ix_risk_categories_category_id", table_name="risk_categories")
    op.drop_table("risk_categories")

    op.drop_index("ix_regulatory_obligations_linked_policy_id", table_name="regulatory_obligations")
    op.drop_column("regulatory_obligations", "linked_policy_id")
