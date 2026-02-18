"""add kyc-tm bridge fields to user risk profiles

Revision ID: 20260218_kyc_tm_bridge
Revises: 20260218_kyc_module_foundations
Create Date: 2026-02-18 16:05:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260218_kyc_tm_bridge"
down_revision = "20260218_kyc_module_foundations"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "user_risk_profiles" not in existing_tables:
        return

    columns = {col["name"] for col in inspector.get_columns("user_risk_profiles")}
    if "compliance_profile_id" not in columns:
        op.add_column(
            "user_risk_profiles",
            sa.Column("compliance_profile_id", sa.Integer(), nullable=True),
        )
    if "kyc_risk_score" not in columns:
        op.add_column(
            "user_risk_profiles",
            sa.Column("kyc_risk_score", sa.Numeric(5, 2), nullable=True),
        )
    if "kyc_cdd_level" not in columns:
        op.add_column(
            "user_risk_profiles",
            sa.Column("kyc_cdd_level", sa.String(length=32), nullable=True),
        )
    if "kyc_pep_status" not in columns:
        op.add_column(
            "user_risk_profiles",
            sa.Column("kyc_pep_status", sa.String(length=20), nullable=True),
        )
    if "kyc_last_synced_at" not in columns:
        op.add_column(
            "user_risk_profiles",
            sa.Column("kyc_last_synced_at", sa.DateTime(), nullable=True),
        )

    inspector = sa.inspect(bind)
    indexes = {idx["name"] for idx in inspector.get_indexes("user_risk_profiles")}
    idx_name = op.f("ix_user_risk_profiles_compliance_profile_id")
    if idx_name not in indexes:
        op.create_index(idx_name, "user_risk_profiles", ["compliance_profile_id"], unique=False)

    fk_names = {fk.get("name") for fk in inspector.get_foreign_keys("user_risk_profiles")}
    fk_name = "fk_user_risk_profiles_compliance_profile_id"
    if fk_name not in fk_names and bind.dialect.name != "sqlite":
        op.create_foreign_key(
            fk_name,
            "user_risk_profiles",
            "compliance_profiles",
            ["compliance_profile_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # Lightweight backfill from existing EDD flag.
    op.execute(
        """
        UPDATE user_risk_profiles
        SET kyc_cdd_level = CASE
            WHEN enhanced_due_diligence = true THEN 'enhanced'
            ELSE COALESCE(kyc_cdd_level, 'standard')
        END
        WHERE kyc_cdd_level IS NULL
        """
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "user_risk_profiles" not in existing_tables:
        return

    fk_names = {fk.get("name") for fk in inspector.get_foreign_keys("user_risk_profiles")}
    fk_name = "fk_user_risk_profiles_compliance_profile_id"
    if fk_name in fk_names and bind.dialect.name != "sqlite":
        op.drop_constraint(fk_name, "user_risk_profiles", type_="foreignkey")

    indexes = {idx["name"] for idx in inspector.get_indexes("user_risk_profiles")}
    idx_name = op.f("ix_user_risk_profiles_compliance_profile_id")
    if idx_name in indexes:
        op.drop_index(idx_name, table_name="user_risk_profiles")

    columns = {col["name"] for col in inspector.get_columns("user_risk_profiles")}
    if "kyc_last_synced_at" in columns:
        op.drop_column("user_risk_profiles", "kyc_last_synced_at")
    if "kyc_pep_status" in columns:
        op.drop_column("user_risk_profiles", "kyc_pep_status")
    if "kyc_cdd_level" in columns:
        op.drop_column("user_risk_profiles", "kyc_cdd_level")
    if "kyc_risk_score" in columns:
        op.drop_column("user_risk_profiles", "kyc_risk_score")
    if "compliance_profile_id" in columns:
        op.drop_column("user_risk_profiles", "compliance_profile_id")
