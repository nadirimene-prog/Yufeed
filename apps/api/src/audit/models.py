"""
Audit, Event, and Decision Models (append-only)
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB

from src.database import Base


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class AuditLog(Base):
    """Append-only audit log for all mutations."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    audit_id = Column(String(64), unique=True, nullable=False, index=True)
    tenant_id = Column(String(255), nullable=False, index=True)

    actor_id = Column(String(255), index=True)
    actor_email = Column(String(255), index=True)
    actor_role = Column(String(50))
    actor_type = Column(String(50), default="user")  # user | system | anonymous
    actor_ip = Column(String(45))
    user_agent = Column(String(500))

    action = Column(String(50), index=True)
    method = Column(String(10))
    path = Column(String(500))
    entity_type = Column(String(100), index=True)
    entity_id = Column(String(255), index=True)
    status_code = Column(Integer)
    request_id = Column(String(64), index=True)

    changes = Column(JSON().with_variant(JSONB(), "postgresql"))
    metadata_json = Column("metadata", JSON().with_variant(JSONB(), "postgresql"))

    created_at = Column(DateTime, default=utc_now, index=True)


class EventRecord(Base):
    """Immutable event record (append-only)."""
    __tablename__ = "event_records"

    id = Column(Integer, primary_key=True)
    event_id = Column(String(64), unique=True, nullable=False, index=True)
    tenant_id = Column(String(255), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(100), index=True)
    entity_id = Column(String(255), index=True)
    source = Column(String(100))
    payload = Column(JSON().with_variant(JSONB(), "postgresql"))
    metadata_json = Column("metadata", JSON().with_variant(JSONB(), "postgresql"))
    created_at = Column(DateTime, default=utc_now, index=True)


class DecisionRecord(Base):
    """Immutable decision record (append-only)."""
    __tablename__ = "decision_records"

    id = Column(Integer, primary_key=True)
    decision_id = Column(String(64), unique=True, nullable=False, index=True)
    tenant_id = Column(String(255), nullable=False, index=True)
    event_id = Column(String(64), ForeignKey("event_records.event_id"), index=True)
    decision = Column(String(20), nullable=False, index=True)  # allow|block|step_up|alert
    reason_codes = Column(JSON().with_variant(JSONB(), "postgresql"))
    rule_version = Column(String(50))
    model_version = Column(String(50))
    evidence = Column(JSON().with_variant(JSONB(), "postgresql"))
    metadata_json = Column("metadata", JSON().with_variant(JSONB(), "postgresql"))
    created_at = Column(DateTime, default=utc_now, index=True)
