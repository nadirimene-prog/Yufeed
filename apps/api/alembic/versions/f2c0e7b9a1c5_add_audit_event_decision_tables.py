"""add_audit_event_decision_tables

Revision ID: f2c0e7b9a1c5
Revises: d123abc45678, cbee3d7ad225
Create Date: 2026-01-22 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2c0e7b9a1c5"
down_revision: Union[str, Sequence[str], None] = ("d123abc45678", "cbee3d7ad225")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add audit/event/decision tables with immutability."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("audit_id", sa.String(length=64), nullable=False),
        sa.Column("actor_id", sa.String(length=255), nullable=True),
        sa.Column("actor_email", sa.String(length=255), nullable=True),
        sa.Column("actor_role", sa.String(length=50), nullable=True),
        sa.Column("actor_type", sa.String(length=50), nullable=True),
        sa.Column("actor_ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=True),
        sa.Column("method", sa.String(length=10), nullable=True),
        sa.Column("path", sa.String(length=500), nullable=True),
        sa.Column("entity_type", sa.String(length=100), nullable=True),
        sa.Column("entity_id", sa.String(length=255), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("changes", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_audit_logs_audit_id", "audit_logs", ["audit_id"], unique=True)
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"])
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    op.create_table(
        "event_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=True),
        sa.Column("entity_id", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_event_records_event_id", "event_records", ["event_id"], unique=True)
    op.create_index("ix_event_records_event_type", "event_records", ["event_type"])
    op.create_index("ix_event_records_entity_type", "event_records", ["entity_type"])
    op.create_index("ix_event_records_entity_id", "event_records", ["entity_id"])
    op.create_index("ix_event_records_created_at", "event_records", ["created_at"])

    op.create_table(
        "decision_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("decision_id", sa.String(length=64), nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=True),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=True),
        sa.Column("rule_version", sa.String(length=50), nullable=True),
        sa.Column("model_version", sa.String(length=50), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    if dialect == "postgresql":
        op.create_foreign_key(
            "fk_decision_records_event_id_event_records",
            "decision_records",
            "event_records",
            ["event_id"],
            ["event_id"],
        )
    op.create_index(
        "ix_decision_records_decision_id", "decision_records", ["decision_id"], unique=True
    )
    op.create_index("ix_decision_records_event_id", "decision_records", ["event_id"])
    op.create_index("ix_decision_records_decision", "decision_records", ["decision"])
    op.create_index("ix_decision_records_created_at", "decision_records", ["created_at"])

    if dialect == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION prevent_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'Immutable table: %', TG_TABLE_NAME;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        for table in ("audit_logs", "event_records", "decision_records"):
            op.execute(
                f"""
                CREATE TRIGGER {table}_immutable_update
                BEFORE UPDATE ON {table}
                FOR EACH ROW EXECUTE FUNCTION prevent_mutation();
                """
            )
            op.execute(
                f"""
                CREATE TRIGGER {table}_immutable_delete
                BEFORE DELETE ON {table}
                FOR EACH ROW EXECUTE FUNCTION prevent_mutation();
                """
            )
    elif dialect == "sqlite":
        for table in ("audit_logs", "event_records", "decision_records"):
            op.execute(
                f"""
                CREATE TRIGGER {table}_immutable_update
                BEFORE UPDATE ON {table}
                BEGIN
                    SELECT RAISE(FAIL, '{table} is immutable');
                END;
                """
            )
            op.execute(
                f"""
                CREATE TRIGGER {table}_immutable_delete
                BEFORE DELETE ON {table}
                BEGIN
                    SELECT RAISE(FAIL, '{table} is immutable');
                END;
                """
            )


def downgrade() -> None:
    """Downgrade schema - drop audit/event/decision tables and immutability."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        for table in ("audit_logs", "event_records", "decision_records"):
            op.execute(f"DROP TRIGGER IF EXISTS {table}_immutable_update ON {table};")
            op.execute(f"DROP TRIGGER IF EXISTS {table}_immutable_delete ON {table};")
        op.execute("DROP FUNCTION IF EXISTS prevent_mutation();")
    elif dialect == "sqlite":
        for table in ("audit_logs", "event_records", "decision_records"):
            op.execute(f"DROP TRIGGER IF EXISTS {table}_immutable_update;")
            op.execute(f"DROP TRIGGER IF EXISTS {table}_immutable_delete;")

    if dialect == "postgresql":
        op.drop_constraint(
            "fk_decision_records_event_id_event_records", "decision_records", type_="foreignkey"
        )
    op.drop_index("ix_decision_records_created_at", table_name="decision_records")
    op.drop_index("ix_decision_records_decision", table_name="decision_records")
    op.drop_index("ix_decision_records_event_id", table_name="decision_records")
    op.drop_index("ix_decision_records_decision_id", table_name="decision_records")
    op.drop_table("decision_records")

    op.drop_index("ix_event_records_created_at", table_name="event_records")
    op.drop_index("ix_event_records_entity_id", table_name="event_records")
    op.drop_index("ix_event_records_entity_type", table_name="event_records")
    op.drop_index("ix_event_records_event_type", table_name="event_records")
    op.drop_index("ix_event_records_event_id", table_name="event_records")
    op.drop_table("event_records")

    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_audit_id", table_name="audit_logs")
    op.drop_table("audit_logs")
