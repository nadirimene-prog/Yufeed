"""kyc module foundations and lifecycle fields

Revision ID: 20260218_kyc_module_foundations
Revises: 20260218_policy_multitenancy
Create Date: 2026-02-18 15:20:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260218_kyc_module_foundations"
down_revision = "20260218_policy_multitenancy"
branch_labels = None
depends_on = None


def _json_type(bind):
    return (
        postgresql.JSONB(astext_type=sa.Text()) if bind.dialect.name == "postgresql" else sa.JSON()
    )


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(idx.get("name") == index_name for idx in inspector.get_indexes(table_name))


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    json_type = _json_type(bind)

    if "compliance_profiles" not in existing_tables:
        op.create_table(
            "compliance_profiles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.String(length=255), nullable=False, server_default="default"),
            sa.Column("user_id", sa.String(length=255), nullable=True),
            sa.Column("status", sa.String(), nullable=False, server_default="pending"),
            sa.Column("risk_level", sa.String(), nullable=False, server_default="low"),
            sa.Column("cdd_level", sa.String(length=32), nullable=False, server_default="standard"),
            sa.Column("cdd_reason", sa.Text(), nullable=True),
            sa.Column("next_review_date", sa.DateTime(), nullable=True),
            sa.Column("last_review_date", sa.DateTime(), nullable=True),
            sa.Column("review_frequency_months", sa.Integer(), nullable=True),
            sa.Column("pep_status", sa.String(length=20), nullable=False, server_default="unknown"),
            sa.Column("pep_details", json_type, nullable=True),
            sa.Column("sanctions_screened_at", sa.DateTime(), nullable=True),
            sa.Column("sanctions_status", sa.String(length=20), nullable=True),
            sa.Column("adverse_media_status", sa.String(length=20), nullable=True),
            sa.Column("source_of_funds", sa.Text(), nullable=True),
            sa.Column("source_of_wealth", sa.Text(), nullable=True),
            sa.Column("occupation", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=True, onupdate=sa.func.now()),
            sa.Column("type", sa.String(), nullable=True),
        )
    else:
        columns = {col["name"] for col in inspector.get_columns("compliance_profiles")}
        if "tenant_id" not in columns:
            op.add_column(
                "compliance_profiles",
                sa.Column("tenant_id", sa.String(length=255), nullable=True),
            )
            op.execute(
                "UPDATE compliance_profiles SET tenant_id = 'default' WHERE tenant_id IS NULL"
            )
        if "user_id" not in columns:
            op.add_column(
                "compliance_profiles",
                sa.Column("user_id", sa.String(length=255), nullable=True),
            )
        if "cdd_level" not in columns:
            op.add_column(
                "compliance_profiles",
                sa.Column("cdd_level", sa.String(length=32), nullable=True),
            )
            op.execute(
                "UPDATE compliance_profiles SET cdd_level = 'standard' WHERE cdd_level IS NULL"
            )
        if "cdd_reason" not in columns:
            op.add_column("compliance_profiles", sa.Column("cdd_reason", sa.Text(), nullable=True))
        if "next_review_date" not in columns:
            op.add_column(
                "compliance_profiles",
                sa.Column("next_review_date", sa.DateTime(), nullable=True),
            )
        if "last_review_date" not in columns:
            op.add_column(
                "compliance_profiles",
                sa.Column("last_review_date", sa.DateTime(), nullable=True),
            )
        if "review_frequency_months" not in columns:
            op.add_column(
                "compliance_profiles",
                sa.Column("review_frequency_months", sa.Integer(), nullable=True),
            )
        if "pep_status" not in columns:
            op.add_column(
                "compliance_profiles",
                sa.Column("pep_status", sa.String(length=20), nullable=True),
            )
            op.execute(
                "UPDATE compliance_profiles SET pep_status = 'unknown' WHERE pep_status IS NULL"
            )
        if "pep_details" not in columns:
            op.add_column(
                "compliance_profiles",
                sa.Column("pep_details", json_type, nullable=True),
            )
        if "sanctions_screened_at" not in columns:
            op.add_column(
                "compliance_profiles",
                sa.Column("sanctions_screened_at", sa.DateTime(), nullable=True),
            )
        if "sanctions_status" not in columns:
            op.add_column(
                "compliance_profiles",
                sa.Column("sanctions_status", sa.String(length=20), nullable=True),
            )
        if "adverse_media_status" not in columns:
            op.add_column(
                "compliance_profiles",
                sa.Column("adverse_media_status", sa.String(length=20), nullable=True),
            )
        if "source_of_funds" not in columns:
            op.add_column(
                "compliance_profiles",
                sa.Column("source_of_funds", sa.Text(), nullable=True),
            )
        if "source_of_wealth" not in columns:
            op.add_column(
                "compliance_profiles",
                sa.Column("source_of_wealth", sa.Text(), nullable=True),
            )
        if "occupation" not in columns:
            op.add_column(
                "compliance_profiles",
                sa.Column("occupation", sa.String(length=255), nullable=True),
            )

    inspector = sa.inspect(bind)
    if "compliance_profiles" in set(inspector.get_table_names()):
        idx_tenant = op.f("ix_compliance_profiles_tenant_id")
        idx_user = op.f("ix_compliance_profiles_user_id")
        idx_next_review = op.f("ix_compliance_profiles_next_review_date")
        if not _has_index(inspector, "compliance_profiles", idx_tenant):
            op.create_index(idx_tenant, "compliance_profiles", ["tenant_id"], unique=False)
        if not _has_index(inspector, "compliance_profiles", idx_user):
            op.create_index(idx_user, "compliance_profiles", ["user_id"], unique=False)
        if not _has_index(inspector, "compliance_profiles", idx_next_review):
            op.create_index(
                idx_next_review, "compliance_profiles", ["next_review_date"], unique=False
            )

    if "compliance_kyc_profiles" not in existing_tables:
        op.create_table(
            "compliance_kyc_profiles",
            sa.Column(
                "id", sa.Integer(), sa.ForeignKey("compliance_profiles.id"), primary_key=True
            ),
            sa.Column("first_name", sa.String(), nullable=False),
            sa.Column("last_name", sa.String(), nullable=False),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("phone_number", sa.String(), nullable=True),
            sa.Column("date_of_birth", sa.DateTime(), nullable=True),
            sa.Column("address_line1", sa.String(), nullable=True),
            sa.Column("city", sa.String(), nullable=True),
            sa.Column("country", sa.String(), nullable=True),
            sa.Column("nationality", sa.String(length=2), nullable=True),
            sa.Column("tax_id", sa.String(length=255), nullable=True),
            sa.Column("id_document_type", sa.String(length=50), nullable=True),
            sa.Column("id_document_number", sa.String(length=255), nullable=True),
            sa.Column("id_expiry_date", sa.DateTime(), nullable=True),
        )
    else:
        columns = {col["name"] for col in inspector.get_columns("compliance_kyc_profiles")}
        if "nationality" not in columns:
            op.add_column(
                "compliance_kyc_profiles",
                sa.Column("nationality", sa.String(length=2), nullable=True),
            )
        if "tax_id" not in columns:
            op.add_column(
                "compliance_kyc_profiles",
                sa.Column("tax_id", sa.String(length=255), nullable=True),
            )
        if "id_document_type" not in columns:
            op.add_column(
                "compliance_kyc_profiles",
                sa.Column("id_document_type", sa.String(length=50), nullable=True),
            )
        if "id_document_number" not in columns:
            op.add_column(
                "compliance_kyc_profiles",
                sa.Column("id_document_number", sa.String(length=255), nullable=True),
            )
        if "id_expiry_date" not in columns:
            op.add_column(
                "compliance_kyc_profiles",
                sa.Column("id_expiry_date", sa.DateTime(), nullable=True),
            )

    inspector = sa.inspect(bind)
    if "compliance_kyc_profiles" in set(inspector.get_table_names()):
        idx_email = op.f("ix_compliance_kyc_profiles_email")
        if not _has_index(inspector, "compliance_kyc_profiles", idx_email):
            op.create_index(idx_email, "compliance_kyc_profiles", ["email"], unique=False)

    if "compliance_kyb_profiles" not in existing_tables:
        op.create_table(
            "compliance_kyb_profiles",
            sa.Column(
                "id", sa.Integer(), sa.ForeignKey("compliance_profiles.id"), primary_key=True
            ),
            sa.Column("company_name", sa.String(), nullable=False),
            sa.Column("registration_number", sa.String(), nullable=False),
            sa.Column("jurisdiction", sa.String(), nullable=False),
            sa.Column("website", sa.String(), nullable=True),
            sa.Column("industry", sa.String(), nullable=True),
            sa.Column("legal_form", sa.String(length=100), nullable=True),
            sa.Column("incorporation_date", sa.DateTime(), nullable=True),
            sa.Column("annual_turnover", sa.String(length=255), nullable=True),
            sa.Column("number_of_employees", sa.Integer(), nullable=True),
            sa.Column("beneficial_ownership_chain", json_type, nullable=True),
        )
    else:
        columns = {col["name"] for col in inspector.get_columns("compliance_kyb_profiles")}
        if "legal_form" not in columns:
            op.add_column(
                "compliance_kyb_profiles",
                sa.Column("legal_form", sa.String(length=100), nullable=True),
            )
        if "incorporation_date" not in columns:
            op.add_column(
                "compliance_kyb_profiles",
                sa.Column("incorporation_date", sa.DateTime(), nullable=True),
            )
        if "annual_turnover" not in columns:
            op.add_column(
                "compliance_kyb_profiles",
                sa.Column("annual_turnover", sa.String(length=255), nullable=True),
            )
        if "number_of_employees" not in columns:
            op.add_column(
                "compliance_kyb_profiles",
                sa.Column("number_of_employees", sa.Integer(), nullable=True),
            )
        if "beneficial_ownership_chain" not in columns:
            op.add_column(
                "compliance_kyb_profiles",
                sa.Column("beneficial_ownership_chain", json_type, nullable=True),
            )

    inspector = sa.inspect(bind)
    if "compliance_kyb_profiles" in set(inspector.get_table_names()):
        idx_reg = op.f("ix_compliance_kyb_profiles_registration_number")
        if not _has_index(inspector, "compliance_kyb_profiles", idx_reg):
            op.create_index(
                idx_reg, "compliance_kyb_profiles", ["registration_number"], unique=False
            )

    if "compliance_documents" not in existing_tables:
        op.create_table(
            "compliance_documents",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.String(length=255), nullable=False, server_default="default"),
            sa.Column(
                "profile_id", sa.Integer(), sa.ForeignKey("compliance_profiles.id"), nullable=True
            ),
            sa.Column("document_type", sa.String(), nullable=False),
            sa.Column("file_url", sa.String(), nullable=False),
            sa.Column("verification_status", sa.String(), nullable=True, server_default="pending"),
            sa.Column("verified_by", sa.String(length=255), nullable=True),
            sa.Column("verified_at", sa.DateTime(), nullable=True),
            sa.Column("rejection_reason", sa.Text(), nullable=True),
            sa.Column("vendor_verification_id", sa.String(length=255), nullable=True),
            sa.Column("vendor_response", json_type, nullable=True),
            sa.Column("expiry_date", sa.DateTime(), nullable=True),
            sa.Column("uploaded_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        )
    else:
        columns = {col["name"] for col in inspector.get_columns("compliance_documents")}
        if "tenant_id" not in columns:
            op.add_column(
                "compliance_documents",
                sa.Column("tenant_id", sa.String(length=255), nullable=True),
            )
            op.execute(
                "UPDATE compliance_documents SET tenant_id = 'default' WHERE tenant_id IS NULL"
            )
        if "verified_by" not in columns:
            op.add_column(
                "compliance_documents",
                sa.Column("verified_by", sa.String(length=255), nullable=True),
            )
        if "verified_at" not in columns:
            op.add_column(
                "compliance_documents",
                sa.Column("verified_at", sa.DateTime(), nullable=True),
            )
        if "rejection_reason" not in columns:
            op.add_column(
                "compliance_documents",
                sa.Column("rejection_reason", sa.Text(), nullable=True),
            )
        if "vendor_verification_id" not in columns:
            op.add_column(
                "compliance_documents",
                sa.Column("vendor_verification_id", sa.String(length=255), nullable=True),
            )
        if "vendor_response" not in columns:
            op.add_column(
                "compliance_documents",
                sa.Column("vendor_response", json_type, nullable=True),
            )
        if "expiry_date" not in columns:
            op.add_column(
                "compliance_documents",
                sa.Column("expiry_date", sa.DateTime(), nullable=True),
            )

    inspector = sa.inspect(bind)
    if "compliance_documents" in set(inspector.get_table_names()):
        idx_tenant = op.f("ix_compliance_documents_tenant_id")
        idx_expiry = op.f("ix_compliance_documents_expiry_date")
        if not _has_index(inspector, "compliance_documents", idx_tenant):
            op.create_index(idx_tenant, "compliance_documents", ["tenant_id"], unique=False)
        if not _has_index(inspector, "compliance_documents", idx_expiry):
            op.create_index(idx_expiry, "compliance_documents", ["expiry_date"], unique=False)

    if "compliance_risk_signals" not in existing_tables:
        op.create_table(
            "compliance_risk_signals",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.String(length=255), nullable=False, server_default="default"),
            sa.Column(
                "profile_id", sa.Integer(), sa.ForeignKey("compliance_profiles.id"), nullable=True
            ),
            sa.Column("user_id", sa.String(length=255), nullable=True),
            sa.Column("signal_type", sa.String(), nullable=False),
            sa.Column("score", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("detected_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        )
    else:
        columns = {col["name"] for col in inspector.get_columns("compliance_risk_signals")}
        if "tenant_id" not in columns:
            op.add_column(
                "compliance_risk_signals",
                sa.Column("tenant_id", sa.String(length=255), nullable=True),
            )
            op.execute(
                "UPDATE compliance_risk_signals SET tenant_id = 'default' WHERE tenant_id IS NULL"
            )
        if "user_id" not in columns:
            op.add_column(
                "compliance_risk_signals",
                sa.Column("user_id", sa.String(length=255), nullable=True),
            )

    inspector = sa.inspect(bind)
    if "compliance_risk_signals" in set(inspector.get_table_names()):
        idx_tenant = op.f("ix_compliance_risk_signals_tenant_id")
        idx_user = op.f("ix_compliance_risk_signals_user_id")
        if not _has_index(inspector, "compliance_risk_signals", idx_tenant):
            op.create_index(idx_tenant, "compliance_risk_signals", ["tenant_id"], unique=False)
        if not _has_index(inspector, "compliance_risk_signals", idx_user):
            op.create_index(idx_user, "compliance_risk_signals", ["user_id"], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    for table_name, indexes in (
        (
            "compliance_risk_signals",
            [
                op.f("ix_compliance_risk_signals_tenant_id"),
                op.f("ix_compliance_risk_signals_user_id"),
            ],
        ),
        (
            "compliance_documents",
            [
                op.f("ix_compliance_documents_tenant_id"),
                op.f("ix_compliance_documents_expiry_date"),
            ],
        ),
        (
            "compliance_kyb_profiles",
            [op.f("ix_compliance_kyb_profiles_registration_number")],
        ),
        (
            "compliance_kyc_profiles",
            [op.f("ix_compliance_kyc_profiles_email")],
        ),
        (
            "compliance_profiles",
            [
                op.f("ix_compliance_profiles_tenant_id"),
                op.f("ix_compliance_profiles_user_id"),
                op.f("ix_compliance_profiles_next_review_date"),
            ],
        ),
    ):
        if table_name in existing_tables:
            table_indexes = {idx["name"] for idx in inspector.get_indexes(table_name)}
            for index_name in indexes:
                if index_name in table_indexes:
                    op.drop_index(index_name, table_name=table_name)

    if "compliance_risk_signals" in existing_tables:
        op.drop_table("compliance_risk_signals")
    if "compliance_documents" in existing_tables:
        op.drop_table("compliance_documents")
    if "compliance_kyb_profiles" in existing_tables:
        op.drop_table("compliance_kyb_profiles")
    if "compliance_kyc_profiles" in existing_tables:
        op.drop_table("compliance_kyc_profiles")
    if "compliance_profiles" in existing_tables:
        op.drop_table("compliance_profiles")
