"""Scheduled KYC lifecycle tasks."""

from __future__ import annotations

import logging
from typing import Dict, List

from sqlalchemy import distinct

from src.database import SessionLocal
from src.models.compliance import ComplianceProfile
from src.services.kyc_finding_bridge import KYCFindingBridge
from src.services.kyc_periodic_review import KYCPeriodicReviewService
from src.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.task_periodic_kyc_review_scan")
def task_periodic_kyc_review_scan(max_profiles_per_tenant: int = 200) -> Dict[str, int]:
    """Scan profiles due for periodic review and emit KYC expiry findings."""
    db = SessionLocal()
    try:
        tenant_ids: List[str] = [
            tenant_id
            for (tenant_id,) in db.query(distinct(ComplianceProfile.tenant_id))
            .filter(ComplianceProfile.tenant_id.is_not(None))
            .all()
            if tenant_id
        ]

        review_service = KYCPeriodicReviewService(db)
        bridge = KYCFindingBridge(db)

        total_due = 0
        findings_created = 0

        for tenant_id in tenant_ids:
            due_profiles = review_service.find_profiles_due_for_review(
                tenant_id=tenant_id,
                limit=max_profiles_per_tenant,
            )
            total_due += len(due_profiles)

            for profile in due_profiles:
                _finding, is_new = bridge.create_kyc_expiry(
                    tenant_id=tenant_id,
                    profile_id=profile.id,
                    user_id=profile.user_id,
                    summary="Periodic KYC review due",
                    details={
                        "next_review_date": (
                            profile.next_review_date.isoformat()
                            if profile.next_review_date
                            else None
                        ),
                    },
                )
                if is_new:
                    findings_created += 1

        db.commit()
        return {
            "tenants_scanned": len(tenant_ids),
            "profiles_due": total_due,
            "findings_created": findings_created,
        }
    except Exception:
        db.rollback()
        logger.exception("task_periodic_kyc_review_scan failed")
        raise
    finally:
        db.close()


@celery_app.task(name="tasks.task_document_expiry_check")
def task_document_expiry_check(days: int = 30) -> Dict[str, int]:
    """Check for KYC documents expiring soon and emit findings."""
    db = SessionLocal()
    try:
        review_service = KYCPeriodicReviewService(db)
        bridge = KYCFindingBridge(db)

        tenant_ids: List[str] = [
            tenant_id
            for (tenant_id,) in db.query(distinct(ComplianceProfile.tenant_id))
            .filter(ComplianceProfile.tenant_id.is_not(None))
            .all()
            if tenant_id
        ]

        processed_docs = 0
        findings_created = 0

        for tenant_id in tenant_ids:
            docs = review_service.find_documents_expiring_in(tenant_id=tenant_id, days=days)
            for doc in docs:
                profile = (
                    db.query(ComplianceProfile)
                    .filter(
                        ComplianceProfile.id == doc.profile_id,
                        ComplianceProfile.tenant_id == tenant_id,
                    )
                    .first()
                )
                processed_docs += 1
                summary = (
                    f"Document '{doc.document_type}' expires on "
                    f"{doc.expiry_date.date().isoformat() if doc.expiry_date else 'unknown'}"
                )
                _finding, is_new = bridge.create_kyc_expiry(
                    tenant_id=tenant_id,
                    profile_id=profile.id if profile else doc.profile_id,
                    user_id=profile.user_id if profile else None,
                    summary=summary,
                    details={
                        "document_id": doc.id,
                        "document_type": doc.document_type,
                        "expiry_date": doc.expiry_date.isoformat() if doc.expiry_date else None,
                    },
                )
                if is_new:
                    findings_created += 1

        db.commit()
        return {
            "tenants_scanned": len(tenant_ids),
            "documents_processed": processed_docs,
            "findings_created": findings_created,
        }
    except Exception:
        db.rollback()
        logger.exception("task_document_expiry_check failed")
        raise
    finally:
        db.close()
