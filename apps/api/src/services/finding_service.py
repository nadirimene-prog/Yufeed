"""Centralized Finding service for idempotent create/update.

All sources (transaction monitoring, obligations, sanctions, reg change)
MUST create findings through this service to guarantee:
- Fingerprint-based deduplication
- Audit trail on every mutation
- Consistent status lifecycle
"""

import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from src.audit.recorders import record_event
from src.models.finding_models import Finding, FindingStatus
from src.utils.time import utc_now

logger = logging.getLogger(__name__)


class FindingService:
    """Idempotent Finding upsert service."""

    def __init__(self, db: Session):
        self.db = db

    def create_or_update_finding(
        self,
        tenant_id: str,
        finding_type: str,
        fingerprint: str,
        severity: Optional[str] = None,
        title: Optional[str] = None,
        summary: Optional[str] = None,
        source_refs: Optional[Dict[str, Any]] = None,
        explainability: Optional[Dict[str, Any]] = None,
        assigned_to: Optional[str] = None,
        sla_due_at: Optional[datetime] = None,
    ) -> Tuple[Finding, bool]:
        """Create a new finding or update an existing one by fingerprint.

        Returns:
            Tuple of (finding, is_new).

        On existing match:
        - Merges source_refs (dict update)
        - Replaces explainability
        - Reopens if currently closed (status → new)
        - Records ``finding.updated`` audit event

        On new:
        - Creates the finding
        - Records ``finding.created`` audit event
        """
        fingerprint = self._normalize_fingerprint(tenant_id, fingerprint)

        existing = (
            self.db.query(Finding)
            .filter(
                Finding.tenant_id == tenant_id,
                Finding.fingerprint == fingerprint,
            )
            .first()
        )

        if existing:
            # Merge source_refs
            if source_refs:
                merged = dict(existing.source_refs_json or {})
                merged.update(source_refs)
                existing.source_refs_json = merged
            if explainability is not None:
                existing.explainability_json = explainability
            if severity is not None:
                existing.severity = severity.lower().strip() or None
            if title is not None:
                existing.title = title
            if summary is not None:
                existing.summary = summary
            # Reopen if previously closed
            if existing.status == FindingStatus.closed.value:
                existing.status = FindingStatus.new.value
                existing.closed_reason = None
                existing.closed_comment = None
            existing.updated_at = utc_now()

            record_event(
                self.db,
                event_type="finding.updated",
                entity_type="finding",
                entity_id=str(existing.id),
                tenant_id=tenant_id,
                payload={
                    "fingerprint": fingerprint,
                    "finding_type": finding_type,
                    "reopened": existing.status == FindingStatus.new.value,
                },
            )
            logger.debug("Updated existing finding id=%s fp=%s", existing.id, fingerprint)
            return existing, False

        finding = Finding(
            tenant_id=tenant_id,
            finding_type=finding_type,
            severity=(severity or "").lower().strip() or None,
            status=FindingStatus.new.value,
            title=title,
            summary=summary,
            source_refs_json=source_refs,
            fingerprint=fingerprint,
            explainability_json=explainability,
            assigned_to=assigned_to,
            sla_due_at=sla_due_at,
        )
        self.db.add(finding)
        self.db.flush()  # assign id without committing

        record_event(
            self.db,
            event_type="finding.created",
            entity_type="finding",
            entity_id=str(finding.id),
            tenant_id=tenant_id,
            payload={
                "fingerprint": fingerprint,
                "finding_type": finding_type,
                "severity": severity,
            },
        )
        logger.info("Created finding id=%s type=%s fp=%s", finding.id, finding_type, fingerprint)
        return finding, True

    def close_finding(
        self,
        finding: Finding,
        closed_reason: str,
        closed_comment: Optional[str],
        actor_id: str,
    ) -> Finding:
        """Close a finding with a reason and optional comment."""
        finding.status = FindingStatus.closed.value
        finding.closed_reason = closed_reason
        finding.closed_comment = closed_comment
        finding.updated_at = utc_now()

        record_event(
            self.db,
            event_type="finding.closed",
            entity_type="finding",
            entity_id=str(finding.id),
            tenant_id=finding.tenant_id,
            payload={
                "closed_reason": closed_reason,
                "actor": actor_id,
            },
        )
        logger.info("Closed finding id=%s reason=%s", finding.id, closed_reason)
        return finding

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_fingerprint(tenant_id: str, fingerprint: str) -> str:
        """Ensure fingerprint is a stable-length string.

        - Short inputs (< 8 chars) are hashed to avoid collisions.
        - Long inputs (> 128 chars) are truncated.
        """
        if len(fingerprint) < 8:
            return hashlib.sha256(f"{tenant_id}:{fingerprint}".encode("utf-8")).hexdigest()[:128]
        if len(fingerprint) > 128:
            return fingerprint[:128]
        return fingerprint
