"""Bridge: sanctions screening results → Findings.

Call ``create_findings_from_screening()`` after any sanctions screening
to materialise hits as triageable Findings.
"""

import logging
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from src.models.finding_models import Finding
from src.services.finding_service import FindingService

logger = logging.getLogger(__name__)


def create_findings_from_screening(
    db: Session,
    tenant_id: str,
    screening_result: Any,
    subject_type: str,
    subject_id: str,
) -> List[Finding]:
    """Create/update Findings from a sanctions screening result.

    Parameters
    ----------
    db : Session
        Active database session (caller must commit).
    tenant_id : str
        Tenant context.
    screening_result : ScreeningResult
        Object with ``.is_hit``, ``.matches``, ``.screened_name``.
    subject_type : str
        E.g. ``"user"`` or ``"entity"``.
    subject_id : str
        Identifier of the screened subject.

    Returns
    -------
    list[Finding]
        Newly created or updated findings.
    """
    if not getattr(screening_result, "is_hit", False):
        return []

    svc = FindingService(db)
    findings: List[Finding] = []

    for match in getattr(screening_result, "matches", []):
        matched_name = getattr(match, "matched_name", getattr(match, "original_name", "unknown"))
        list_type = getattr(match, "list_type", "unknown")
        score = getattr(match, "score", 0)

        # Build a stable fingerprint
        fp = f"{tenant_id}:SANCTIONS_HIT:{subject_id}:{matched_name}:{list_type}"

        severity = "critical" if score >= 95 else "high"

        source_refs: Dict[str, Any] = {
            "subject_type": subject_type,
            "subject_id": subject_id,
            "list_type": str(list_type),
            "matched_name": matched_name,
        }
        if hasattr(match, "list_sources"):
            source_refs["list_sources"] = match.list_sources

        explainability: Dict[str, Any] = {
            "match_score": score,
            "matched_name": matched_name,
        }
        for attr in ("aliases", "nationalities", "birth_dates", "addresses", "programs"):
            val = getattr(match, attr, None)
            if val:
                explainability[attr] = val

        screened_name = getattr(screening_result, "screened_name", subject_id)

        finding, _is_new = svc.create_or_update_finding(
            tenant_id=tenant_id,
            finding_type="SANCTIONS_HIT",
            fingerprint=fp,
            severity=severity,
            title=f"Sanctions match: {matched_name} ({list_type})",
            summary=(
                f"Name '{screened_name}' matched against {matched_name} "
                f"(score: {score}) on list {list_type}"
            ),
            source_refs=source_refs,
            explainability=explainability,
        )
        findings.append(finding)

    logger.info(
        "Created %d sanctions findings for subject %s/%s",
        len(findings),
        subject_type,
        subject_id,
    )
    return findings
