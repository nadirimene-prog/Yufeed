from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import JSONB

from src.database import Base


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class TravelRuleRequestRecord(Base):
    """Persisted Travel Rule requests for audit evidence."""
    __tablename__ = "travel_rule_requests"

    id = Column(Integer, primary_key=True)
    request_id = Column(String(64), unique=True, nullable=False, index=True)
    transaction_id = Column(String(255), nullable=False, index=True)
    amount = Column(String(50), nullable=False)
    currency = Column(String(10), nullable=False)
    asset = Column(String(50))
    originator = Column(JSON().with_variant(JSONB(), "postgresql"))
    beneficiary = Column(JSON().with_variant(JSONB(), "postgresql"))
    message = Column(Text)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    submitted_at = Column(DateTime)
