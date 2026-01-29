from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from src.database import Base


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)

class Annotation(Base):
    """Internal notes and annotations on legal documents for compliance team."""
    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(Integer, ForeignKey("legal_documents.id"), nullable=False)
    user_email = Column(String, nullable=False)  # User who created the annotation
    content = Column(Text, nullable=False)
    article_reference = Column(String, nullable=True)  # e.g., "Article 5(3)"
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    document = relationship("LegalDocument", backref="annotations")
