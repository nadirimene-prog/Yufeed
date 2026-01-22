"""
Common enumerations used across the application.

Centralized enum definitions to avoid duplication and ensure consistency.
"""
import enum


class ComplianceStatus(str, enum.Enum):
    """Status of a compliance profile or case."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MANUAL_REVIEW = "manual_review"


class RiskLevel(str, enum.Enum):
    """
    Risk level classification for documents, transactions, profiles, etc.

    Consolidated from:
    - models/compliance.py
    - models/models.py
    - schemas/compliance.py
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"  # For cases where risk level hasn't been assessed


class AlertStatus(str, enum.Enum):
    """Status of a transaction alert."""
    OPEN = "open"
    INVESTIGATING = "investigating"
    ESCALATED = "escalated"
    CLOSED = "closed"
    FALSE_POSITIVE = "false_positive"


class CaseStatus(str, enum.Enum):
    """Status of a compliance case."""
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    ESCALATED = "escalated"
    CLOSED = "closed"
    RESOLVED = "resolved"
