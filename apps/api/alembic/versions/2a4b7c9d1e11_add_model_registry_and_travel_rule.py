"""add_model_registry_and_travel_rule

Revision ID: 2a4b7c9d1e11
Revises: 9f3c2b1a7d55
Create Date: 2026-01-22 19:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "2a4b7c9d1e11"
down_revision: Union[str, Sequence[str], None] = "9f3c2b1a7d55"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    json_type = postgresql.JSONB() if dialect == "postgresql" else sa.JSON()

    op.create_table(
        "model_registry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_id", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("model_type", sa.String(100), nullable=False),
        sa.Column("owner", sa.String(255)),
        sa.Column("status", sa.String(50), server_default="active"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_model_registry_model_id", "model_registry", ["model_id"])

    op.create_table(
        "model_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_id", sa.Integer(), sa.ForeignKey("model_registry.id"), nullable=False),
        sa.Column("version", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), server_default="staging"),
        sa.Column("artifact_uri", sa.String(500)),
        sa.Column("feature_set_hash", sa.String(128)),
        sa.Column("training_window", sa.String(255)),
        sa.Column("metrics", json_type),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("promoted_at", sa.DateTime()),
    )
    op.create_index("ix_model_versions_model_id", "model_versions", ["model_id"])

    op.create_table(
        "model_drift_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_version_id", sa.Integer(), sa.ForeignKey("model_versions.id"), nullable=False),
        sa.Column("drift_score", sa.Numeric(6, 3)),
        sa.Column("status", sa.String(50), server_default="ok"),
        sa.Column("window_start", sa.DateTime()),
        sa.Column("window_end", sa.DateTime()),
        sa.Column("metrics", json_type),
        sa.Column("observed_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_model_drift_reports_version_id", "model_drift_reports", ["model_version_id"])

    op.create_table(
        "travel_rule_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.String(64), nullable=False, unique=True),
        sa.Column("transaction_id", sa.String(255), nullable=False),
        sa.Column("amount", sa.String(50), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("asset", sa.String(50)),
        sa.Column("originator", json_type),
        sa.Column("beneficiary", json_type),
        sa.Column("message", sa.Text()),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("submitted_at", sa.DateTime()),
    )
    op.create_index("ix_travel_rule_requests_request_id", "travel_rule_requests", ["request_id"])


def downgrade() -> None:
    op.drop_index("ix_travel_rule_requests_request_id", table_name="travel_rule_requests")
    op.drop_table("travel_rule_requests")

    op.drop_index("ix_model_drift_reports_version_id", table_name="model_drift_reports")
    op.drop_table("model_drift_reports")

    op.drop_index("ix_model_versions_model_id", table_name="model_versions")
    op.drop_table("model_versions")

    op.drop_index("ix_model_registry_model_id", table_name="model_registry")
    op.drop_table("model_registry")
