"""
Reports Module
Aggregates all reporting routers.
"""

from fastapi import APIRouter

from .sar_filing import router as sar_filing_router
from .evidence import router as evidence_router
from .compliance_dashboard import router as compliance_dashboard_router
from .scope_analysis import router as scope_analysis_router
from .audit_trails import router as audit_trails_router


# Create main router for reports
router = APIRouter()

# Include all sub-routers
router.include_router(sar_filing_router)
router.include_router(evidence_router)
router.include_router(compliance_dashboard_router)
router.include_router(scope_analysis_router)
router.include_router(audit_trails_router)
