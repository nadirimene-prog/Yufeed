"""add immutable audit_logs

Revision ID: 20240128_add_audit_logs
Revises: f2c0e7b9a1c5   # <-- replace with the ID you just saw (or edit later)
Create Date: 2024-01-28 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20240128_add_audit_logs"
down_revision = "f2c0e7b9a1c5"   # <-- SAME value as above
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("audit_id", sa.String(255), nullable=False, unique=True),
        sa.Column("actor_id", sa.String(255), nullable=True),
        sa.Column("actor_email", sa.String(255), nullable=True),
        sa.Column("actor_role", sa.String(50), nullable=True),
        sa.Column("actor_type", sa.String(50), nullable=True),
        sa.Column("actor_ip", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("path", sa.String(512), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=True),
        sa.Column("entity_id", sa.String(255), nullable=True),
        sa.Column("status_code", sa.Integer, nullable=True),
        sa.Column("request_id", sa.String(255), nullable=True),
        sa.Column("changes", sa.JSON, nullable=True),
        sa.Column("metadata_json", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    # Immutable – any UPDATE/DELETE will raise an exception
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_audit_mod()
        RETURNS trigger AS 61713
        BEGIN
            RAISE EXCEPTION 'audit_logs is immutable';
        END;
        61713 LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_no_update
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION prevent_audit_mod();
        """
    )


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS audit_no_update ON audit_logs")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_mod")
    op.drop_table("audit_logs")
