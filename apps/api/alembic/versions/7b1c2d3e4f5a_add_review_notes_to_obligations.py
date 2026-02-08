"""add_review_notes_to_obligations

Revision ID: 7b1c2d3e4f5a
Revises: 6c9d1a2b3c4d
Create Date: 2026-01-24 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "7b1c2d3e4f5a"
down_revision: Union[str, Sequence[str], None] = "6c9d1a2b3c4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("regulatory_obligations", sa.Column("review_notes", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("regulatory_obligations", "review_notes")
