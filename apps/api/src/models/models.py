from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Text, Table, ARRAY, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
import enum
from datetime import datetime, timezone
from src.database import Base


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)

class DocType(str, enum.Enum):
    REGULATION = "regulation"
    DIRECTIVE = "directive"
    DECISION = "decision"
    OTHER = "other"

class ComplianceDomain(str, enum.Enum):
    AML = "aml"
    CFT = "cft"
    SANCTIONS = "sanctions"
    KYC = "kyc"
    CDD = "cdd"
    PAYMENTS = "payments"
    CRYPTO = "crypto"
    GDPR = "gdpr"
    OTHER = "other"

class RiskLevel(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"

class VersionKind(str, enum.Enum):
    INITIAL = "initial"
    CONSOLIDATED = "consolidated"
    CORRIGENDUM = "corrigendum"

class AlertEventType(str, enum.Enum):
    NEW_DOC = "new_doc"
    UPDATED_DOC = "updated_doc"
    NEW_VERSION = "new_version"

class LegalDocument(Base):
    __tablename__ = "legal_documents"

    id = Column(Integer, primary_key=True, index=True)
    celex = Column(String, unique=True, index=True, nullable=False)
    source_system = Column(String, nullable=True)  # eur-lex, legifrance, esma, eba
    source_reference = Column(String, nullable=True)  # original source identifier
    jurisdiction = Column(String, nullable=True)  # EU, FR
    primary_language = Column(String, default="en")
    eli = Column(String, index=True, nullable=True)
    cellar_id = Column(String, unique=True, index=True, nullable=True)
    title = Column(Text, nullable=False)
    type = Column(String, nullable=True) 
    publication_date = Column(DateTime, nullable=True)
    entry_into_force_date = Column(DateTime, nullable=True)
    status = Column(String, default="active")
    last_modified = Column(DateTime, default=utc_now)
    
    # AMLRO Compliance Fields
    compliance_domain = Column(String, nullable=True)  # ComplianceDomain enum
    risk_level = Column(String, default="unknown")  # RiskLevel enum
    implementation_deadline = Column(DateTime, nullable=True)
    jurisdictional_scope = Column(String, nullable=True)  # e.g., "EU-wide", "Member State"
    obligations_json = Column(JSON().with_variant(JSONB(), "postgresql"), nullable=True)  # Extracted obligations
    ai_summary = Column(Text, nullable=True)  # AI-generated summary
    analyzed_at = Column(DateTime, nullable=True)  # When AI analysis was performed
    scope_tags = Column(JSON().with_variant(JSONB(), "postgresql"), nullable=True)  # psp/eme/vasp tags
    oj_act_identifier = Column(String, nullable=True)  # e.g., L_202302386
    oj_signature_identifier = Column(String, nullable=True)  # e.g., L_202302386_SIG

    # Document Content Fields
    full_text = Column(Text, nullable=True)  # Extracted full text content
    article_breakdown = Column(JSON().with_variant(JSONB(), "postgresql"), nullable=True)  # Structured articles
    content_extraction_method = Column(String, nullable=True)  # html, pdf, xml
    content_extracted_at = Column(DateTime, nullable=True)  # When content was extracted
    word_count = Column(Integer, nullable=True)  # Document word count
    
    versions = relationship("LegalVersion", back_populates="document")
    texts = relationship("LegalDocumentText", backref="document", cascade="all, delete-orphan")
    # alert_events = relationship("AlertEvent", back_populates="document")
    
    # Relationships for LegalRelation
    relations_from = relationship("LegalRelation", foreign_keys="[LegalRelation.from_doc_id]", back_populates="from_document")
    relations_to = relationship("LegalRelation", foreign_keys="[LegalRelation.to_doc_id]", back_populates="to_document")

class LegalVersion(Base):
    __tablename__ = "legal_versions"

    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(Integer, ForeignKey("legal_documents.id"))
    kind = Column(String, default=VersionKind.INITIAL)
    language = Column(String, default="en")
    source_url = Column(String, nullable=True)
    content_hash = Column(String, nullable=True)
    retrieved_at = Column(DateTime, default=utc_now)
    
    document = relationship("LegalDocument", back_populates="versions")

class LegalRelation(Base):
    __tablename__ = "legal_relations"

    id = Column(Integer, primary_key=True, index=True)
    from_doc_id = Column(Integer, ForeignKey("legal_documents.id"), nullable=False)
    relation_type = Column(String, nullable=False)
    to_doc_id = Column(Integer, ForeignKey("legal_documents.id"), nullable=False)

    from_document = relationship("LegalDocument", foreign_keys=[from_doc_id], back_populates="relations_from")
    to_document = relationship("LegalDocument", foreign_keys=[to_doc_id], back_populates="relations_to")

# Transaction Monitoring and Rule Engine models are located in transaction_models.py
