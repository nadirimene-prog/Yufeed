"""add_content_extraction_fields

Revision ID: 85ede8b442bb
Revises: cb34606e633b
Create Date: 2026-01-08 07:55:33.669498

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '85ede8b442bb'
down_revision: Union[str, Sequence[str], None] = 'cb34606e633b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add content extraction fields
    op.add_column('legal_documents', sa.Column('full_text', sa.Text(), nullable=True))
    op.add_column('legal_documents', sa.Column('article_breakdown', sa.dialects.postgresql.JSONB(), nullable=True))
    op.add_column('legal_documents', sa.Column('content_extraction_method', sa.String(), nullable=True))
    op.add_column('legal_documents', sa.Column('content_extracted_at', sa.DateTime(), nullable=True))
    op.add_column('legal_documents', sa.Column('word_count', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove content extraction fields
    op.drop_column('legal_documents', 'word_count')
    op.drop_column('legal_documents', 'content_extracted_at')
    op.drop_column('legal_documents', 'content_extraction_method')
    op.drop_column('legal_documents', 'article_breakdown')
    op.drop_column('legal_documents', 'full_text')
