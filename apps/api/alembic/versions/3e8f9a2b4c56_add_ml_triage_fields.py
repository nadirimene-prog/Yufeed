"""add ml triage fields to alerts

Revision ID: 3e8f9a2b4c56
Revises: 2a4b7c9d1e11
Create Date: 2026-01-23 12:00:00.000000

Phase 4B: Task 4.4 - Auto-Triage Integration
Adds ML prediction fields to alerts table for intelligent alert triage.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '3e8f9a2b4c56'
down_revision = '2a4b7c9d1e11'
branch_labels = None
depends_on = None


def upgrade():
    """Add ML triage fields to alerts table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("alerts")}
    json_type = postgresql.JSONB(astext_type=sa.Text()) if bind.dialect.name == "postgresql" else sa.JSON()

    if "ml_prediction" not in columns:
        op.add_column("alerts", sa.Column("ml_prediction", sa.String(length=50), nullable=True))
    if "ml_confidence" not in columns:
        op.add_column("alerts", sa.Column("ml_confidence", sa.Numeric(precision=5, scale=4), nullable=True))
    if "ml_model_version" not in columns:
        op.add_column("alerts", sa.Column("ml_model_version", sa.String(length=50), nullable=True))
    if "ml_features_snapshot" not in columns:
        op.add_column("alerts", sa.Column("ml_features_snapshot", json_type, nullable=True))

    index_name = op.f("ix_alerts_ml_prediction")
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("alerts")}
    if index_name not in existing_indexes:
        op.create_index(index_name, "alerts", ["ml_prediction"], unique=False)


def downgrade():
    """Remove ML triage fields from alerts table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("alerts")}
    index_name = op.f("ix_alerts_ml_prediction")
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("alerts")}

    if index_name in existing_indexes:
        op.drop_index(index_name, table_name="alerts")

    if "ml_features_snapshot" in columns:
        op.drop_column("alerts", "ml_features_snapshot")
    if "ml_model_version" in columns:
        op.drop_column("alerts", "ml_model_version")
    if "ml_confidence" in columns:
        op.drop_column("alerts", "ml_confidence")
    if "ml_prediction" in columns:
        op.drop_column("alerts", "ml_prediction")
