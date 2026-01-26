from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, JSON, Date
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from src.database import Base


class RegulatorySource(Base):
    __tablename__ = "regulatory_sources"

    id = Column(Integer, primary_key=True)
    source_key = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    jurisdiction = Column(String(100), nullable=False)  # EU, FR
    language = Column(String(10), nullable=False, default="en")
    source_type = Column(String(50), nullable=False, default="rss")  # rss | api
    base_url = Column(String(1000), nullable=True)
    schedule = Column(String(50), nullable=True, default="weekly")
    is_active = Column(Boolean, default=True)
    last_ingested_at = Column(DateTime, nullable=True)
    metadata_json = Column("metadata", JSON().with_variant(JSONB(), "postgresql"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    runs = relationship("IngestionRun", back_populates="source", cascade="all, delete-orphan")


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("regulatory_sources.id"), nullable=False)
    status = Column(String(50), default="running")  # running | completed | failed
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    items_seen = Column(Integer, default=0)
    items_new = Column(Integer, default=0)
    items_updated = Column(Integer, default=0)
    errors_json = Column("errors", JSON().with_variant(JSONB(), "postgresql"), nullable=True)

    source = relationship("RegulatorySource", back_populates="runs")


class OfficialJournalAct(Base):
    __tablename__ = "official_journal_acts"

    id = Column(Integer, primary_key=True)
    act_identifier = Column(String(255), unique=True, nullable=False, index=True)
    act_uri = Column(String(1000), nullable=True)
    signature_identifier = Column(String(255), nullable=True)
    signature_uri = Column(String(1000), nullable=True)
    publication_date = Column(Date, nullable=False, index=True)
    series = Column(String(10), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LegalDocumentText(Base):
    __tablename__ = "legal_document_texts"

    id = Column(Integer, primary_key=True)
    doc_id = Column(Integer, ForeignKey("legal_documents.id"), nullable=False, index=True)
    language = Column(String(10), nullable=False, default="en")
    full_text = Column(Text, nullable=True)
    article_breakdown = Column(JSON().with_variant(JSONB(), "postgresql"), nullable=True)
    content_extraction_method = Column(String(50), nullable=True)
    content_extracted_at = Column(DateTime, nullable=True)
    word_count = Column(Integer, nullable=True)
    source_url = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RegulatoryObligation(Base):
    __tablename__ = "regulatory_obligations"

    id = Column(Integer, primary_key=True)
    obligation_id = Column(String(64), unique=True, nullable=False, index=True)
    doc_id = Column(Integer, ForeignKey("legal_documents.id"), nullable=False, index=True)
    celex = Column(String(64), nullable=True)
    article_ref = Column(String(255), nullable=True)
    obligation_text = Column(Text, nullable=False)
    applicability = Column(Text, nullable=True)
    effective_date = Column(DateTime, nullable=True)
    status = Column(String(50), default="draft")  # draft | in_review | approved | rejected | deprecated
    created_by = Column(String(255), nullable=True)
    reviewed_by = Column(String(255), nullable=True)
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    scope_tags = Column(JSON().with_variant(JSONB(), "postgresql"), nullable=True)
    tags_json = Column("tags", JSON().with_variant(JSONB(), "postgresql"), nullable=True)
    evidence_json = Column("evidence", JSON().with_variant(JSONB(), "postgresql"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    document = relationship("LegalDocument", backref="obligations")


class PolicyDocument(Base):
    __tablename__ = "policy_documents"

    id = Column(Integer, primary_key=True)
    policy_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=True)
    owner = Column(String(255), nullable=True)
    status = Column(String(50), default="draft")  # draft | approved | active | retired
    language = Column(String(10), default="en")
    effective_date = Column(DateTime, nullable=True)
    last_reviewed_at = Column(DateTime, nullable=True)
    source_url = Column(String(1000), nullable=True)
    content = Column(Text, nullable=True)
    metadata_json = Column("metadata", JSON().with_variant(JSONB(), "postgresql"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sections = relationship("PolicySection", back_populates="policy", cascade="all, delete-orphan")


class PolicySection(Base):
    __tablename__ = "policy_sections"

    id = Column(Integer, primary_key=True)
    policy_id = Column(Integer, ForeignKey("policy_documents.id"), nullable=False, index=True)
    section_ref = Column(String(100), nullable=True)
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=True)
    status = Column(String(50), default="draft")
    version = Column(String(50), nullable=True)
    last_reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    policy = relationship("PolicyDocument", back_populates="sections")


class InternalRule(Base):
    __tablename__ = "internal_rules"

    id = Column(Integer, primary_key=True)
    internal_rule_id = Column(String(64), unique=True, nullable=False, index=True)
    obligation_id = Column(Integer, ForeignKey("regulatory_obligations.id"), nullable=False, index=True)
    policy_section_id = Column(Integer, ForeignKey("policy_sections.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    control_owner = Column(String(255), nullable=True)
    status = Column(String(50), default="draft")  # draft | in_review | approved | implemented | archived
    reviewed_by = Column(String(255), nullable=True)
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    obligation = relationship("RegulatoryObligation", backref="internal_rules")
    policy_section = relationship("PolicySection")


class InternalRuleMapping(Base):
    __tablename__ = "internal_rule_mappings"

    id = Column(Integer, primary_key=True)
    internal_rule_id = Column(Integer, ForeignKey("internal_rules.id"), nullable=False, index=True)
    monitoring_rule_id = Column(Integer, ForeignKey("monitoring_rules.id"), nullable=True, index=True)
    mapping_type = Column(String(50), default="transaction_monitoring")
    created_at = Column(DateTime, default=datetime.utcnow)

    internal_rule = relationship("InternalRule", backref="mappings")
