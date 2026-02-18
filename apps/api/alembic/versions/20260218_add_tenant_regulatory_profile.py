"""add tenant regulatory profile model and tenant institution fields

Revision ID: 20260218_tenant_reg_profile
Revises: 20260211_case_notes
Create Date: 2026-02-18 10:45:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260218_tenant_reg_profile"
down_revision = "20260211_case_notes"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    json_type = (
        postgresql.JSONB(astext_type=sa.Text()) if bind.dialect.name == "postgresql" else sa.JSON()
    )

    if "tenants" in existing_tables:
        tenant_columns = {col["name"] for col in inspector.get_columns("tenants")}
        if "institution_type" not in tenant_columns:
            op.add_column(
                "tenants", sa.Column("institution_type", sa.String(length=50), nullable=True)
            )
        if "license_number" not in tenant_columns:
            op.add_column(
                "tenants", sa.Column("license_number", sa.String(length=255), nullable=True)
            )
        if "license_jurisdiction" not in tenant_columns:
            op.add_column(
                "tenants",
                sa.Column("license_jurisdiction", sa.String(length=10), nullable=True),
            )
        if "supervisory_authority" not in tenant_columns:
            op.add_column(
                "tenants",
                sa.Column("supervisory_authority", sa.String(length=255), nullable=True),
            )
        if "regulatory_scope_tags" not in tenant_columns:
            op.add_column("tenants", sa.Column("regulatory_scope_tags", json_type, nullable=True))

        tenant_indexes = {idx["name"] for idx in inspector.get_indexes("tenants")}
        institution_type_index = op.f("ix_tenants_institution_type")
        if institution_type_index not in tenant_indexes:
            op.create_index(institution_type_index, "tenants", ["institution_type"], unique=False)

    if "tenant_regulatory_profiles" not in existing_tables:
        op.create_table(
            "tenant_regulatory_profiles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("regulation_doc_id", sa.Integer(), nullable=False),
            sa.Column("applicability", sa.String(length=20), nullable=False, server_default="full"),
            sa.Column("applicability_notes", sa.Text(), nullable=True),
            sa.Column("effective_from", sa.DateTime(), nullable=True),
            sa.Column("created_by", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=True, onupdate=sa.func.now()),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["regulation_doc_id"], ["legal_documents.id"], ondelete="CASCADE"
            ),
            sa.UniqueConstraint(
                "tenant_id", "regulation_doc_id", name="uq_tenant_regulatory_profile"
            ),
        )

    if "tenant_regulatory_profiles" in set(sa.inspect(bind).get_table_names()):
        profile_indexes = {
            idx["name"] for idx in sa.inspect(bind).get_indexes("tenant_regulatory_profiles")
        }
        profile_tenant_index = op.f("ix_tenant_regulatory_profiles_tenant_id")
        profile_doc_index = op.f("ix_tenant_regulatory_profiles_regulation_doc_id")
        if profile_tenant_index not in profile_indexes:
            op.create_index(
                profile_tenant_index,
                "tenant_regulatory_profiles",
                ["tenant_id"],
                unique=False,
            )
        if profile_doc_index not in profile_indexes:
            op.create_index(
                profile_doc_index,
                "tenant_regulatory_profiles",
                ["regulation_doc_id"],
                unique=False,
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "tenant_regulatory_profiles" in existing_tables:
        profile_indexes = {
            idx["name"] for idx in inspector.get_indexes("tenant_regulatory_profiles")
        }
        profile_tenant_index = op.f("ix_tenant_regulatory_profiles_tenant_id")
        profile_doc_index = op.f("ix_tenant_regulatory_profiles_regulation_doc_id")
        if profile_doc_index in profile_indexes:
            op.drop_index(profile_doc_index, table_name="tenant_regulatory_profiles")
        if profile_tenant_index in profile_indexes:
            op.drop_index(profile_tenant_index, table_name="tenant_regulatory_profiles")
        op.drop_table("tenant_regulatory_profiles")

    if "tenants" in existing_tables:
        tenant_indexes = {idx["name"] for idx in inspector.get_indexes("tenants")}
        institution_type_index = op.f("ix_tenants_institution_type")
        if institution_type_index in tenant_indexes:
            op.drop_index(institution_type_index, table_name="tenants")

        tenant_columns = {col["name"] for col in inspector.get_columns("tenants")}
        if "regulatory_scope_tags" in tenant_columns:
            op.drop_column("tenants", "regulatory_scope_tags")
        if "supervisory_authority" in tenant_columns:
            op.drop_column("tenants", "supervisory_authority")
        if "license_jurisdiction" in tenant_columns:
            op.drop_column("tenants", "license_jurisdiction")
        if "license_number" in tenant_columns:
            op.drop_column("tenants", "license_number")
        if "institution_type" in tenant_columns:
            op.drop_column("tenants", "institution_type")
