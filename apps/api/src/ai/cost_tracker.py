"""
AI cost tracking utilities.

Currently a lightweight shim to avoid breaking ingestion flows.
"""
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


def log_usage_from_analysis(
    db,
    analysis: Dict[str, Any],
    document_id: Optional[int] = None,
    obligation_id: Optional[int] = None,
) -> None:
    """
    Best-effort logging of AI usage from an analysis payload.
    This is a no-op if the payload does not include usage details.
    """
    try:
        usage = analysis.get("usage") or {}
        if not usage:
            return
        # Placeholder: actual persistence is not wired in current model layer.
        logger.info(
            "AI usage recorded (doc_id=%s, obligation_id=%s, usage=%s)",
            document_id,
            obligation_id,
            usage,
        )
    except Exception as exc:
        logger.debug("AI usage logging skipped: %s", exc)
