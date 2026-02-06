"""Add feature_values unique constraints for tenant scoping.

Revision ID: p0q1r2s3t4u5
Revises: n8o9p0q1r2s3
Create Date: 2026-02-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "p0q1r2s3t4u5"
down_revision: Union[str, Sequence[str], None] = "n8o9p0q1r2s3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FEATURE_VALUES_UNIQUE = "uq_feature_values_tenant_entity_feature_version"
FEATURE_VALUES_INDEX = "ix_feature_values_tenant_entity"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "feature_values" not in inspector.get_table_names():
        return

    unique_constraints = {c["name"] for c in inspector.get_unique_constraints("feature_values")}
    indexes = {i["name"] for i in inspector.get_indexes("feature_values")}

    if FEATURE_VALUES_UNIQUE not in unique_constraints:
        op.create_unique_constraint(
            FEATURE_VALUES_UNIQUE,
            "feature_values",
            ["tenant_id", "entity_type", "entity_id", "feature_name", "version"],
        )

    if FEATURE_VALUES_INDEX not in indexes:
        op.create_index(
            FEATURE_VALUES_INDEX,
            "feature_values",
            ["tenant_id", "entity_type", "entity_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "feature_values" not in inspector.get_table_names():
        return

    indexes = {i["name"] for i in inspector.get_indexes("feature_values")}
    if FEATURE_VALUES_INDEX in indexes:
        op.drop_index(FEATURE_VALUES_INDEX, table_name="feature_values")

    unique_constraints = {c["name"] for c in inspector.get_unique_constraints("feature_values")}
    if FEATURE_VALUES_UNIQUE in unique_constraints:
        op.drop_constraint(FEATURE_VALUES_UNIQUE, "feature_values", type_="unique")

