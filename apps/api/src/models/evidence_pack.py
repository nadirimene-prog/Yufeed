"""EvidencePack model — audit-proof snapshot of a case.

An EvidencePack captures a point-in-time snapshot of a case, its findings,
decisions, and audit trail.  The snapshot is canonicalised and SHA-256 hashed
to guarantee integrity.
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Index, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from src.database import Base
from src.utils.time import utc_now


class EvidencePack(Base):
    __tablename__ = "evidence_packs"
    __table_args__ = (
        Index("ix_evidence_packs_case_id", "case_id"),
        Index("ix_evidence_packs_tenant_id", "tenant_id"),
    )

    id = Column(Integer, primary_key=True)
    pack_id = Column(String(64), unique=True, nullable=False, index=True)
    tenant_id = Column(String(255), nullable=False)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)

    schema_version = Column(String(20), nullable=False, default="v1")
    version = Column(Integer, nullable=False, default=1)
    format = Column(String(10), nullable=False, default="json")  # json | pdf

    # The full snapshot (canonical JSON)
    snapshot_json = Column(
        "snapshot",
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
    )

    # SHA-256 of the canonical JSON
    integrity_hash = Column(String(64), nullable=False)

    # Optional file path for PDF packs
    storage_ref = Column(String(500), nullable=True)

    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=utc_now)

    case = relationship("Case", backref="evidence_packs")
