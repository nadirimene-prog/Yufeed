"""
SAR/UAR Filing API
Endpoints for Suspicious Activity Reports and Unusual Activity Reports.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.transaction_models import Case
from src.compliance.sar_filing import SARFilingSystem, UARFilingSystem
from src.auth.dependencies import require_any_role, CurrentUser
from src.utils.event_bus import publish_event_safe

router = APIRouter(prefix="/reporting", tags=["sar-filing"])


@router.post("/sar/prepare/{case_id}")
def prepare_sar(
    case_id: str,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "analyst", "aml_officer"])),
):
    """
    Prepare Suspicious Activity Report from a case.

    Returns complete SAR structure ready for filing.
    """
    sar_system = SARFilingSystem(db)

    try:
        sar = sar_system.prepare_sar(case_id)
        publish_event_safe(
            "events.raw",
            {
                "event_type": "sar.prepared",
                "entity_type": "case",
                "entity_id": case_id,
                "source": "reporting",
                "payload": {
                    "case_id": case_id,
                },
            },
        )
        return sar

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SAR preparation failed: {str(e)}")


@router.post("/sar/file/{case_id}")
def file_sar(
    case_id: str,
    jurisdiction: str = Query("EU", pattern="^(US|EU|INTL)$"),
    dry_run: bool = Query(True),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    """
    File SAR with regulatory authority.

    jurisdiction: US (FinCEN), EU (National FIU), INTL (goAML)
    dry_run: If True, validates but doesn't submit
    """
    sar_system = SARFilingSystem(db)

    try:
        # Prepare SAR
        sar = sar_system.prepare_sar(case_id)

        # File SAR
        result = sar_system.file_sar(sar, jurisdiction, dry_run)

        # Update case if actually filed
        if not dry_run:
            case = db.query(Case).filter(Case.case_id == case_id).first()
            if case:
                case.outcome = "sar_filed"
                case.outcome_notes = f"SAR filed: {result['filing_reference']}"
                db.commit()

        publish_event_safe(
            "events.raw",
            {
                "event_type": "sar.filed",
                "entity_type": "case",
                "entity_id": case_id,
                "source": "reporting",
                "payload": {
                    "case_id": case_id,
                    "jurisdiction": jurisdiction,
                    "dry_run": dry_run,
                    "filing_reference": result.get("filing_reference"),
                },
            },
        )
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SAR filing failed: {str(e)}")


@router.post("/uar/prepare/{alert_id}")
def prepare_uar(
    alert_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "analyst", "aml_officer"])),
):
    """
    Prepare Unusual Activity Report from an alert.
    """
    uar_system = UARFilingSystem(db)

    try:
        uar = uar_system.prepare_uar(alert_id)
        publish_event_safe(
            "events.raw",
            {
                "event_type": "uar.prepared",
                "entity_type": "alert",
                "entity_id": str(alert_id),
                "source": "reporting",
                "payload": {
                    "alert_id": alert_id,
                },
            },
        )
        return uar

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"UAR preparation failed: {str(e)}")
