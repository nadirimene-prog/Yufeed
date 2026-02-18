"""add compliance calendar events table

Revision ID: 20260218_compliance_calendar
Revises: 20260218_kyc_tm_bridge
Create Date: 2026-02-18 17:10:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260218_compliance_calendar"
down_revision = "20260218_kyc_tm_bridge"
branch_labels = None
depends_on = None


def _json_type(bind):
    return (
        postgresql.JSONB(astext_type=sa.Text()) if bind.dialect.name == "postgresql" else sa.JSON()
    )


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    json_type = _json_type(bind)

    if "compliance_calendar_events" not in existing_tables:
        op.create_table(
            "compliance_calendar_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.String(length=255), nullable=False),
            sa.Column("event_type", sa.String(length=64), nullable=False),
            sa.Column("fingerprint", sa.String(length=128), nullable=False),
            sa.Column("title", sa.String(length=500), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("due_date", sa.DateTime(), nullable=True),
            sa.Column("regulation_doc_id", sa.Integer(), nullable=True),
            sa.Column("obligation_id", sa.Integer(), nullable=True),
            sa.Column("policy_id", sa.Integer(), nullable=True),
            sa.Column("compliance_profile_id", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("assigned_to", sa.String(length=255), nullable=True),
            sa.Column("priority", sa.String(length=16), nullable=False, server_default="medium"),
            sa.Column("reminder_days_before", sa.Integer(), nullable=False, server_default="7"),
            sa.Column("reminder_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_reminder_at", sa.DateTime(), nullable=True),
            sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("metadata", json_type, nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=True, onupdate=sa.func.now()),
            sa.ForeignKeyConstraint(
                ["regulation_doc_id"], ["legal_documents.id"], ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(
                ["obligation_id"], ["regulatory_obligations.id"], ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(["policy_id"], ["policy_documents.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(
                ["compliance_profile_id"], ["compliance_profiles.id"], ondelete="SET NULL"
            ),
            sa.UniqueConstraint(
                "tenant_id",
                "fingerprint",
                name="uq_compliance_calendar_tenant_fingerprint",
            ),
        )

    inspector = sa.inspect(bind)
    indexes = {idx["name"] for idx in inspector.get_indexes("compliance_calendar_events")}
    desired_indexes = [
        (op.f("ix_compliance_calendar_events_tenant_id"), ["tenant_id"]),
        (op.f("ix_compliance_calendar_events_event_type"), ["event_type"]),
        (op.f("ix_compliance_calendar_events_fingerprint"), ["fingerprint"]),
        (op.f("ix_compliance_calendar_events_due_date"), ["due_date"]),
        (op.f("ix_compliance_calendar_events_regulation_doc_id"), ["regulation_doc_id"]),
        (op.f("ix_compliance_calendar_events_obligation_id"), ["obligation_id"]),
        (op.f("ix_compliance_calendar_events_policy_id"), ["policy_id"]),
        (op.f("ix_compliance_calendar_events_compliance_profile_id"), ["compliance_profile_id"]),
        (op.f("ix_compliance_calendar_events_status"), ["status"]),
        (op.f("ix_compliance_calendar_events_assigned_to"), ["assigned_to"]),
    ]
    for index_name, columns in desired_indexes:
        if index_name not in indexes:
            op.create_index(index_name, "compliance_calendar_events", columns, unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "compliance_calendar_events" not in existing_tables:
        return

    indexes = {idx["name"] for idx in inspector.get_indexes("compliance_calendar_events")}
    for index_name in [
        op.f("ix_compliance_calendar_events_assigned_to"),
        op.f("ix_compliance_calendar_events_status"),
        op.f("ix_compliance_calendar_events_compliance_profile_id"),
        op.f("ix_compliance_calendar_events_policy_id"),
        op.f("ix_compliance_calendar_events_obligation_id"),
        op.f("ix_compliance_calendar_events_regulation_doc_id"),
        op.f("ix_compliance_calendar_events_due_date"),
        op.f("ix_compliance_calendar_events_fingerprint"),
        op.f("ix_compliance_calendar_events_event_type"),
        op.f("ix_compliance_calendar_events_tenant_id"),
    ]:
        if index_name in indexes:
            op.drop_index(index_name, table_name="compliance_calendar_events")

    op.drop_table("compliance_calendar_events")
