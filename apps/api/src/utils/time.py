"""
Centralized time utilities for the application.

This module provides a single source of truth for UTC time handling
to avoid duplicate definitions across the codebase.
"""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """
    Return current UTC time (timezone-aware).

    This is the canonical way to get the current UTC time across the application.
    All modules should import and use this function instead of defining their own.

    Returns:
        datetime: Current UTC time with timezone information
    """
    return datetime.now(timezone.utc)
