"""
Compliance Reporting API
Regulatory reporting, analytics, and audit trails.

This module aggregates all reporting endpoints from the reports/ subdirectory.
"""
from fastapi import APIRouter

# Import the aggregated router from reports module
from src.api.reports import router as reports_router


# Main router - no prefix since sub-routers already have /api/reporting
router = reports_router
