"""policy multi-tenancy, tenant obligation applicability, and ORM mappings

Revision ID: 20260218_policy_multitenancy
Revises: 20260218_tenant_reg_profile
Create Date: 2026-02-18 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260218_policy_multitenancy"
down_revision = "20260218_tenant_reg_profile"
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

    if "policy_documents" in existing_tables:
        columns = {col["name"] for col in inspector.get_columns("policy_documents")}
        if "tenant_id" not in columns:
            op.add_column(
                "policy_documents", sa.Column("tenant_id", sa.String(length=255), nullable=True)
            )
        if "is_master" not in columns:
            op.add_column(
                "policy_documents",
                sa.Column(
                    "is_master", sa.Boolean(), nullable=False, server_default=sa.text("false")
                ),
            )
        if "master_policy_id" not in columns:
            op.add_column(
                "policy_documents",
                sa.Column("master_policy_id", sa.Integer(), sa.ForeignKey("policy_documents.id")),
            )

        indexes = {idx["name"] for idx in inspector.get_indexes("policy_documents")}
        idx_tenant = op.f("ix_policy_documents_tenant_id")
        idx_master_policy = op.f("ix_policy_documents_master_policy_id")
        if idx_tenant not in indexes:
            op.create_index(idx_tenant, "policy_documents", ["tenant_id"], unique=False)
        if idx_master_policy not in indexes:
            op.create_index(
                idx_master_policy, "policy_documents", ["master_policy_id"], unique=False
            )

        if bind.dialect.name == "postgresql":
            op.execute(
                """
                UPDATE policy_documents
                SET is_master = TRUE
                WHERE tenant_id IS NULL
                  AND (
                    metadata ->> 'is_master_policy' = 'true'
                    OR policy_id IN (SELECT template_id FROM policy_templates)
                  )
                """
            )
        elif bind.dialect.name == "sqlite":
            op.execute(
                """
                UPDATE policy_documents
                SET is_master = 1
                WHERE tenant_id IS NULL
                  AND (
                    json_extract(metadata, '$.is_master_policy') = 'true'
                    OR policy_id IN (SELECT template_id FROM policy_templates)
                  )
                """
            )

    if "policy_templates" in existing_tables:
        columns = {col["name"] for col in inspector.get_columns("policy_templates")}
        if "institution_types" not in columns:
            op.add_column(
                "policy_templates", sa.Column("institution_types", json_type, nullable=True)
            )
        if "applicable_regulations" not in columns:
            op.add_column(
                "policy_templates",
                sa.Column("applicable_regulations", json_type, nullable=True),
            )

    if "internal_rules" in existing_tables:
        columns = {col["name"] for col in inspector.get_columns("internal_rules")}
        if "tenant_id" not in columns:
            op.add_column(
                "internal_rules", sa.Column("tenant_id", sa.String(length=255), nullable=True)
            )
        indexes = {idx["name"] for idx in inspector.get_indexes("internal_rules")}
        idx_name = op.f("ix_internal_rules_tenant_id")
        if idx_name not in indexes:
            op.create_index(idx_name, "internal_rules", ["tenant_id"], unique=False)

    if "internal_rule_mappings" in existing_tables:
        columns = {col["name"] for col in inspector.get_columns("internal_rule_mappings")}
        if "tenant_id" not in columns:
            op.add_column(
                "internal_rule_mappings",
                sa.Column("tenant_id", sa.String(length=255), nullable=True),
            )
        indexes = {idx["name"] for idx in inspector.get_indexes("internal_rule_mappings")}
        idx_name = op.f("ix_internal_rule_mappings_tenant_id")
        if idx_name not in indexes:
            op.create_index(idx_name, "internal_rule_mappings", ["tenant_id"], unique=False)

    # Backfill tenant_id on internal rules/mappings where resolvable.
    if "internal_rules" in existing_tables and "regulatory_obligations" in existing_tables:
        if bind.dialect.name == "postgresql":
            op.execute(
                """
                UPDATE internal_rules ir
                SET tenant_id = pd.tenant_id
                FROM regulatory_obligations ro
                LEFT JOIN policy_documents pd ON pd.id = ro.linked_policy_id
                WHERE ir.obligation_id = ro.id
                  AND ir.tenant_id IS NULL
                """
            )
        elif bind.dialect.name == "sqlite":
            op.execute(
                """
                UPDATE internal_rules
                SET tenant_id = (
                    SELECT pd.tenant_id
                    FROM regulatory_obligations ro
                    LEFT JOIN policy_documents pd ON pd.id = ro.linked_policy_id
                    WHERE ro.id = internal_rules.obligation_id
                )
                WHERE tenant_id IS NULL
                """
            )

    if "internal_rule_mappings" in existing_tables and "internal_rules" in existing_tables:
        if bind.dialect.name == "postgresql":
            op.execute(
                """
                UPDATE internal_rule_mappings irm
                SET tenant_id = ir.tenant_id
                FROM internal_rules ir
                WHERE irm.internal_rule_id = ir.id
                  AND irm.tenant_id IS NULL
                """
            )
        elif bind.dialect.name == "sqlite":
            op.execute(
                """
                UPDATE internal_rule_mappings
                SET tenant_id = (
                    SELECT ir.tenant_id
                    FROM internal_rules ir
                    WHERE ir.id = internal_rule_mappings.internal_rule_id
                )
                WHERE tenant_id IS NULL
                """
            )

    if "tenant_obligation_applicability" not in existing_tables:
        op.create_table(
            "tenant_obligation_applicability",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.String(length=255), nullable=False),
            sa.Column("obligation_id", sa.Integer(), nullable=False),
            sa.Column(
                "applicability", sa.String(length=32), nullable=False, server_default="applicable"
            ),
            sa.Column("assessed_by", sa.String(length=255), nullable=True),
            sa.Column("assessed_at", sa.DateTime(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=True, onupdate=sa.func.now()),
            sa.ForeignKeyConstraint(
                ["obligation_id"], ["regulatory_obligations.id"], ondelete="CASCADE"
            ),
            sa.UniqueConstraint(
                "tenant_id",
                "obligation_id",
                name="uq_tenant_obligation_applicability",
            ),
        )
    if "tenant_obligation_applicability" in set(sa.inspect(bind).get_table_names()):
        indexes = {
            idx["name"] for idx in sa.inspect(bind).get_indexes("tenant_obligation_applicability")
        }
        idx_tenant = op.f("ix_tenant_obligation_applicability_tenant_id")
        idx_obl = op.f("ix_tenant_obligation_applicability_obligation_id")
        if idx_tenant not in indexes:
            op.create_index(
                idx_tenant, "tenant_obligation_applicability", ["tenant_id"], unique=False
            )
        if idx_obl not in indexes:
            op.create_index(
                idx_obl, "tenant_obligation_applicability", ["obligation_id"], unique=False
            )

    # Create/upgrade obligation_policy_mappings as first-class ORM table.
    if "obligation_policy_mappings" not in existing_tables:
        op.create_table(
            "obligation_policy_mappings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("obligation_id", sa.Integer(), nullable=False),
            sa.Column("policy_id", sa.Integer(), nullable=False),
            sa.Column("mapped_by", sa.String(length=255), nullable=True),
            sa.Column("mapping_confidence", sa.Float(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("mapped_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
            sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=True, onupdate=sa.func.now()),
            sa.ForeignKeyConstraint(
                ["obligation_id"], ["regulatory_obligations.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["policy_id"], ["policy_documents.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("obligation_id", "policy_id", name="uq_obligation_policy_mapping"),
        )
    else:
        columns = {col["name"] for col in inspector.get_columns("obligation_policy_mappings")}
        if "mapped_by" not in columns:
            op.add_column(
                "obligation_policy_mappings",
                sa.Column("mapped_by", sa.String(length=255), nullable=True),
            )
        if "mapping_confidence" not in columns:
            op.add_column(
                "obligation_policy_mappings",
                sa.Column("mapping_confidence", sa.Float(), nullable=True),
            )
        if "notes" not in columns:
            op.add_column(
                "obligation_policy_mappings", sa.Column("notes", sa.Text(), nullable=True)
            )
        if "mapped_at" not in columns:
            op.add_column(
                "obligation_policy_mappings",
                sa.Column("mapped_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
            )
        if "created_at" not in columns:
            op.add_column(
                "obligation_policy_mappings",
                sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
            )
        if "updated_at" not in columns:
            op.add_column(
                "obligation_policy_mappings",
                sa.Column("updated_at", sa.DateTime(), nullable=True, onupdate=sa.func.now()),
            )

        existing_uniques = {
            uc["name"] for uc in inspector.get_unique_constraints("obligation_policy_mappings")
        }
        if "uq_obligation_policy_mapping" not in existing_uniques:
            op.create_unique_constraint(
                "uq_obligation_policy_mapping",
                "obligation_policy_mappings",
                ["obligation_id", "policy_id"],
            )

    if "obligation_policy_mappings" in set(sa.inspect(bind).get_table_names()):
        indexes = {
            idx["name"] for idx in sa.inspect(bind).get_indexes("obligation_policy_mappings")
        }
        idx_obl = op.f("ix_obligation_policy_mappings_obligation_id")
        idx_policy = op.f("ix_obligation_policy_mappings_policy_id")
        if idx_obl not in indexes:
            op.create_index(idx_obl, "obligation_policy_mappings", ["obligation_id"], unique=False)
        if idx_policy not in indexes:
            op.create_index(idx_policy, "obligation_policy_mappings", ["policy_id"], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "obligation_policy_mappings" in existing_tables:
        indexes = {idx["name"] for idx in inspector.get_indexes("obligation_policy_mappings")}
        idx_obl = op.f("ix_obligation_policy_mappings_obligation_id")
        idx_policy = op.f("ix_obligation_policy_mappings_policy_id")
        if idx_policy in indexes:
            op.drop_index(idx_policy, table_name="obligation_policy_mappings")
        if idx_obl in indexes:
            op.drop_index(idx_obl, table_name="obligation_policy_mappings")
        op.drop_table("obligation_policy_mappings")

    if "tenant_obligation_applicability" in existing_tables:
        indexes = {idx["name"] for idx in inspector.get_indexes("tenant_obligation_applicability")}
        idx_tenant = op.f("ix_tenant_obligation_applicability_tenant_id")
        idx_obl = op.f("ix_tenant_obligation_applicability_obligation_id")
        if idx_obl in indexes:
            op.drop_index(idx_obl, table_name="tenant_obligation_applicability")
        if idx_tenant in indexes:
            op.drop_index(idx_tenant, table_name="tenant_obligation_applicability")
        op.drop_table("tenant_obligation_applicability")

    if "internal_rule_mappings" in existing_tables:
        indexes = {idx["name"] for idx in inspector.get_indexes("internal_rule_mappings")}
        idx_name = op.f("ix_internal_rule_mappings_tenant_id")
        if idx_name in indexes:
            op.drop_index(idx_name, table_name="internal_rule_mappings")
        columns = {col["name"] for col in inspector.get_columns("internal_rule_mappings")}
        if "tenant_id" in columns:
            op.drop_column("internal_rule_mappings", "tenant_id")

    if "internal_rules" in existing_tables:
        indexes = {idx["name"] for idx in inspector.get_indexes("internal_rules")}
        idx_name = op.f("ix_internal_rules_tenant_id")
        if idx_name in indexes:
            op.drop_index(idx_name, table_name="internal_rules")
        columns = {col["name"] for col in inspector.get_columns("internal_rules")}
        if "tenant_id" in columns:
            op.drop_column("internal_rules", "tenant_id")

    if "policy_templates" in existing_tables:
        columns = {col["name"] for col in inspector.get_columns("policy_templates")}
        if "applicable_regulations" in columns:
            op.drop_column("policy_templates", "applicable_regulations")
        if "institution_types" in columns:
            op.drop_column("policy_templates", "institution_types")

    if "policy_documents" in existing_tables:
        indexes = {idx["name"] for idx in inspector.get_indexes("policy_documents")}
        idx_tenant = op.f("ix_policy_documents_tenant_id")
        idx_master_policy = op.f("ix_policy_documents_master_policy_id")
        if idx_master_policy in indexes:
            op.drop_index(idx_master_policy, table_name="policy_documents")
        if idx_tenant in indexes:
            op.drop_index(idx_tenant, table_name="policy_documents")

        columns = {col["name"] for col in inspector.get_columns("policy_documents")}
        if "master_policy_id" in columns:
            op.drop_column("policy_documents", "master_policy_id")
        if "is_master" in columns:
            op.drop_column("policy_documents", "is_master")
        if "tenant_id" in columns:
            op.drop_column("policy_documents", "tenant_id")
