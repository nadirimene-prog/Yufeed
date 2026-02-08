"""add scope tags to documents and obligations

Revision ID: 8f2d9a1c4e6b
Revises: 7b1c2d3e4f5a
Create Date: 2026-01-24 23:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "8f2d9a1c4e6b"
down_revision: Union[str, Sequence[str], None] = "7b1c2d3e4f5a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    json_type = (
        postgresql.JSONB(astext_type=sa.Text()) if bind.dialect.name == "postgresql" else sa.JSON()
    )
    op.add_column("legal_documents", sa.Column("scope_tags", json_type, nullable=True))
    op.add_column("regulatory_obligations", sa.Column("scope_tags", json_type, nullable=True))


def downgrade() -> None:
    op.drop_column("regulatory_obligations", "scope_tags")
    op.drop_column("legal_documents", "scope_tags")
