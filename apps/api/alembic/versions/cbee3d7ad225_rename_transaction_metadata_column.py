"""rename_transaction_metadata_column

Revision ID: cbee3d7ad225
Revises: c62fa69a5718
Create Date: 2026-01-08 16:24:00.759297

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cbee3d7ad225'
down_revision: Union[str, Sequence[str], None] = 'c62fa69a5718'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Rename metadata column to transaction_metadata."""
    op.alter_column('transactions', 'metadata', new_column_name='transaction_metadata')


def downgrade() -> None:
    """Downgrade schema - Rename transaction_metadata back to metadata."""
    op.alter_column('transactions', 'transaction_metadata', new_column_name='metadata')
