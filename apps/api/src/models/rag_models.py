"""
RAG Chunk Models
Stores document chunks for retrieval and auditing.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from src.database import Base


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class LegalChunk(Base):
    """Chunked legal document content for RAG retrieval."""
    __tablename__ = "legal_chunks"

    id = Column(Integer, primary_key=True)
    chunk_id = Column(String(255), unique=True, nullable=False, index=True)

    doc_id = Column(Integer, ForeignKey("legal_documents.id"), nullable=False, index=True)
    celex = Column(String, index=True, nullable=False)

    source_system = Column(String, nullable=True)
    jurisdiction = Column(String, nullable=True)
    language = Column(String, nullable=True)

    section_title = Column(Text, nullable=True)
    article_ref = Column(String(100), nullable=True)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)

    token_count = Column(Integer, nullable=True)
    char_count = Column(Integer, nullable=True)

    metadata_json = Column("metadata", JSON().with_variant(JSONB(), "postgresql"), nullable=True)

    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    document = relationship("LegalDocument")

