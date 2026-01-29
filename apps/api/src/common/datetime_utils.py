"""
DateTime Utilities

Provides timezone-aware datetime utilities for consistent timestamp handling.
Uses Python 3.11+ recommended patterns (datetime.utcnow() is deprecated).
"""
from datetime import datetime, timezone


def utc_now() -> datetime:
    """
    Return current UTC time as timezone-aware datetime.

    This replaces the deprecated datetime.utcnow() which returns
    a naive datetime object.

    Returns:
        Timezone-aware datetime in UTC
    """
    return datetime.now(timezone.utc)


def ensure_utc(dt: datetime) -> datetime:
    """
    Ensure a datetime is timezone-aware in UTC.

    If the datetime is naive (no timezone), it assumes UTC and adds tzinfo.
    If the datetime has a different timezone, it converts to UTC.

    Args:
        dt: Datetime to convert (naive or aware)

    Returns:
        Timezone-aware datetime in UTC
    """
    if dt.tzinfo is None:
        # Naive datetime - assume it was UTC
        return dt.replace(tzinfo=timezone.utc)
    else:
        # Convert to UTC
        return dt.astimezone(timezone.utc)


def format_iso(dt: datetime) -> str:
    """
    Format datetime as ISO 8601 string with UTC timezone.

    Args:
        dt: Datetime to format

    Returns:
        ISO 8601 formatted string (e.g., "2024-01-15T10:30:00+00:00")
    """
    return ensure_utc(dt).isoformat()
