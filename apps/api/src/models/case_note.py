"""CaseNote model — investigation notes attached to cases.

Follows the pattern of ``annotation.py`` but scoped to cases.
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship

from src.database import Base
from src.utils.time import utc_now


class CaseNote(Base):
    __tablename__ = "case_notes"
    __table_args__ = (
        Index("ix_case_notes_case_id", "case_id"),
        Index("ix_case_notes_tenant_id", "tenant_id"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(255), nullable=False)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(String(255), nullable=False)
    author_email = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    note_type = Column(String(50), nullable=False, default="general")
    created_at = Column(DateTime, default=utc_now)

    case = relationship("Case", backref="notes")
