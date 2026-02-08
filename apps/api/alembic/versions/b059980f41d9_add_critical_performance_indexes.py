"""add_critical_performance_indexes

Revision ID: b059980f41d9
Revises: 85ede8b442bb
Create Date: 2026-01-08 08:09:08.543813

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b059980f41d9"
down_revision: Union[str, Sequence[str], None] = "85ede8b442bb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add critical performance indexes."""
    # Add indexes for frequently queried fields
    op.create_index(
        "ix_legal_documents_compliance_domain", "legal_documents", ["compliance_domain"]
    )
    op.create_index("ix_legal_documents_risk_level", "legal_documents", ["risk_level"])
    op.create_index(
        "ix_legal_documents_implementation_deadline", "legal_documents", ["implementation_deadline"]
    )
    op.create_index("ix_legal_documents_status", "legal_documents", ["status"])
    op.create_index("ix_legal_documents_publication_date", "legal_documents", ["publication_date"])

    # Composite indexes for common query patterns
    op.create_index(
        "ix_legal_documents_deadline_status",
        "legal_documents",
        ["implementation_deadline", "status"],
    )
    op.create_index(
        "ix_legal_documents_risk_domain", "legal_documents", ["risk_level", "compliance_domain"]
    )


def downgrade() -> None:
    """Downgrade schema - Remove performance indexes."""
    op.drop_index("ix_legal_documents_risk_domain", "legal_documents")
    op.drop_index("ix_legal_documents_deadline_status", "legal_documents")
    op.drop_index("ix_legal_documents_publication_date", "legal_documents")
    op.drop_index("ix_legal_documents_status", "legal_documents")
    op.drop_index("ix_legal_documents_implementation_deadline", "legal_documents")
    op.drop_index("ix_legal_documents_risk_level", "legal_documents")
    op.drop_index("ix_legal_documents_compliance_domain", "legal_documents")
