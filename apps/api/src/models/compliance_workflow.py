from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, JSON, Date
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from src.database import Base


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


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
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    runs = relationship("IngestionRun", back_populates="source", cascade="all, delete-orphan")


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("regulatory_sources.id"), nullable=False)
    status = Column(String(50), default="running")  # running | completed | failed
    started_at = Column(DateTime, default=utc_now)
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
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


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
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class RegulatoryObligation(Base):
    __tablename__ = "regulatory_obligations"

    id = Column(Integer, primary_key=True)
    obligation_id = Column(String(64), unique=True, nullable=False, index=True)
    doc_id = Column(Integer, ForeignKey("legal_documents.id"), nullable=False, index=True)
    linked_policy_id = Column(Integer, ForeignKey("policy_documents.id"), nullable=True, index=True)
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
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    document = relationship("LegalDocument", backref="obligations")
    linked_policy = relationship("PolicyDocument", backref="linked_obligations")


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
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

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
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

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
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    obligation = relationship("RegulatoryObligation", backref="internal_rules")
    policy_section = relationship("PolicySection")


class InternalRuleMapping(Base):
    __tablename__ = "internal_rule_mappings"

    id = Column(Integer, primary_key=True)
    internal_rule_id = Column(Integer, ForeignKey("internal_rules.id"), nullable=False, index=True)
    monitoring_rule_id = Column(Integer, ForeignKey("monitoring_rules.id"), nullable=True, index=True)
    mapping_type = Column(String(50), default="transaction_monitoring")
    created_at = Column(DateTime, default=utc_now)

    internal_rule = relationship("InternalRule", backref="mappings")


class RiskCategory(Base):
    """Business risk categories (Regulatory, Operational, Financial, Reputational)"""
    __tablename__ = "risk_categories"

    id = Column(Integer, primary_key=True)
    category_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    parent_id = Column(Integer, ForeignKey("risk_categories.id"), nullable=True)
    risk_level = Column(String(50), default="medium")  # low | medium | high | critical
    status = Column(String(50), default="active")  # active | inactive
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    parent = relationship("RiskCategory", remote_side=[id], backref="children")
    risk_entries = relationship("RiskEntry", back_populates="category", cascade="all, delete-orphan")


class RiskEntry(Base):
    """Individual risk items linked to obligations"""
    __tablename__ = "risk_entries"

    id = Column(Integer, primary_key=True)
    risk_id = Column(String(64), unique=True, nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("risk_categories.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    inherent_risk_level = Column(String(50), default="medium")  # low | medium | high | critical
    residual_risk_level = Column(String(50), default="medium")  # low | medium | high | critical
    likelihood = Column(String(50), nullable=True)  # rare | unlikely | possible | likely | almost_certain
    impact = Column(String(50), nullable=True)  # insignificant | minor | moderate | major | catastrophic
    mitigation_status = Column(String(50), default="not_started")  # not_started | in_progress | implemented | monitored
    control_owner = Column(String(255), nullable=True)
    review_date = Column(DateTime, nullable=True)
    metadata_json = Column("metadata", JSON().with_variant(JSONB(), "postgresql"), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    category = relationship("RiskCategory", back_populates="risk_entries")
    obligation_links = relationship("ObligationRiskLink", back_populates="risk_entry", cascade="all, delete-orphan")


class ObligationRiskLink(Base):
    """Many-to-many link between obligations and risks"""
    __tablename__ = "obligation_risk_links"

    id = Column(Integer, primary_key=True)
    obligation_id = Column(Integer, ForeignKey("regulatory_obligations.id"), nullable=False, index=True)
    risk_entry_id = Column(Integer, ForeignKey("risk_entries.id"), nullable=False, index=True)
    link_type = Column(String(50), default="mitigates")  # mitigates | addresses | monitors
    notes = Column(Text, nullable=True)
    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    obligation = relationship("RegulatoryObligation", backref="risk_links")
    risk_entry = relationship("RiskEntry", back_populates="obligation_links")
