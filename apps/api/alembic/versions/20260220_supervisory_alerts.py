"""Add supervisory alerts and link obligations to alerts.

Revision ID: 20260220_supervisory_alerts
Revises: 20260219_case_comments_threading
Create Date: 2026-02-20 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260220_supervisory_alerts"
down_revision = "20260219_case_comments_threading"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "supervisory_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dedup_key", sa.String(length=64), nullable=False),
        sa.Column("source_system", sa.String(length=64), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("link", sa.String(length=1000), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("jurisdiction", sa.String(length=32), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=True),
        sa.Column("topics", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="new"),
        sa.Column("raw_entry", sa.JSON(), nullable=True),
        sa.Column("legal_doc_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["legal_doc_id"], ["legal_documents.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedup_key"),
    )
    op.create_index(
        op.f("ix_supervisory_alerts_dedup_key"),
        "supervisory_alerts",
        ["dedup_key"],
        unique=True,
    )
    op.create_index(
        op.f("ix_supervisory_alerts_source_system"),
        "supervisory_alerts",
        ["source_system"],
        unique=False,
    )
    op.create_index(
        op.f("ix_supervisory_alerts_published_at"),
        "supervisory_alerts",
        ["published_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_supervisory_alerts_jurisdiction"),
        "supervisory_alerts",
        ["jurisdiction"],
        unique=False,
    )
    op.create_index(
        op.f("ix_supervisory_alerts_status"),
        "supervisory_alerts",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_supervisory_alerts_legal_doc_id"),
        "supervisory_alerts",
        ["legal_doc_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_supervisory_alerts_created_at"),
        "supervisory_alerts",
        ["created_at"],
        unique=False,
    )

    op.add_column(
        "regulatory_obligations",
        sa.Column("supervisory_alert_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f("ix_regulatory_obligations_supervisory_alert_id"),
        "regulatory_obligations",
        ["supervisory_alert_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_regulatory_obligations_supervisory_alert_id",
        "regulatory_obligations",
        "supervisory_alerts",
        ["supervisory_alert_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_regulatory_obligations_supervisory_alert_id",
        "regulatory_obligations",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_regulatory_obligations_supervisory_alert_id"),
        table_name="regulatory_obligations",
    )
    op.drop_column("regulatory_obligations", "supervisory_alert_id")

    op.drop_index(op.f("ix_supervisory_alerts_created_at"), table_name="supervisory_alerts")
    op.drop_index(op.f("ix_supervisory_alerts_legal_doc_id"), table_name="supervisory_alerts")
    op.drop_index(op.f("ix_supervisory_alerts_status"), table_name="supervisory_alerts")
    op.drop_index(op.f("ix_supervisory_alerts_jurisdiction"), table_name="supervisory_alerts")
    op.drop_index(op.f("ix_supervisory_alerts_published_at"), table_name="supervisory_alerts")
    op.drop_index(op.f("ix_supervisory_alerts_source_system"), table_name="supervisory_alerts")
    op.drop_index(op.f("ix_supervisory_alerts_dedup_key"), table_name="supervisory_alerts")
    op.drop_table("supervisory_alerts")
