"""Compliance calendar service."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from src.models.compliance import ComplianceProfile
from src.models.compliance_calendar import ComplianceCalendarEvent
from src.models.compliance_workflow import (
    PolicyDocument,
    RegulatoryObligation,
    TenantObligationApplicability,
)
from src.models.models import LegalDocument

APPLICABLE_OBLIGATION_STATUSES = {"applicable", "partially_applicable"}
ACTIVE_EVENT_STATUSES = {"pending", "acknowledged", "in_progress", "overdue"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ComplianceCalendarService:
    """Track compliance deadlines and review workflows in one calendar."""

    def __init__(self, db: Session):
        self.db = db

    def list_events(
        self,
        *,
        tenant_id: str,
        status: Optional[str] = None,
        event_type: Optional[str] = None,
        due_before: Optional[datetime] = None,
        due_after: Optional[datetime] = None,
        limit: int = 200,
    ) -> List[ComplianceCalendarEvent]:
        query = self.db.query(ComplianceCalendarEvent).filter(
            ComplianceCalendarEvent.tenant_id == tenant_id
        )

        if status:
            query = query.filter(ComplianceCalendarEvent.status == status)
        if event_type:
            query = query.filter(ComplianceCalendarEvent.event_type == event_type)
        if due_before:
            query = query.filter(ComplianceCalendarEvent.due_date <= due_before)
        if due_after:
            query = query.filter(ComplianceCalendarEvent.due_date >= due_after)

        return (
            query.order_by(ComplianceCalendarEvent.due_date.asc(), ComplianceCalendarEvent.id.asc())
            .limit(limit)
            .all()
        )

    def seed_events_from_obligations(self, tenant_id: str) -> int:
        obligations = (
            self.db.query(RegulatoryObligation)
            .outerjoin(
                TenantObligationApplicability,
                and_(
                    TenantObligationApplicability.obligation_id == RegulatoryObligation.id,
                    TenantObligationApplicability.tenant_id == tenant_id,
                ),
            )
            .filter(
                RegulatoryObligation.effective_date.is_not(None),
                RegulatoryObligation.status.notin_(["rejected", "deprecated"]),
                or_(
                    TenantObligationApplicability.id.is_(None),
                    TenantObligationApplicability.applicability.in_(APPLICABLE_OBLIGATION_STATUSES),
                ),
            )
            .all()
        )

        created = 0
        for obligation in obligations:
            document = (
                self.db.query(LegalDocument).filter(LegalDocument.id == obligation.doc_id).first()
            )
            event = self._create_or_update_event(
                tenant_id=tenant_id,
                event_type="obligation_deadline",
                due_date=obligation.effective_date,
                title=f"Obligation deadline: {obligation.obligation_id}",
                description=obligation.obligation_text[:500],
                regulation_doc_id=obligation.doc_id,
                obligation_id=obligation.id,
                policy_id=obligation.linked_policy_id,
                reminder_days_before=14,
                metadata={
                    "celex": document.celex if document else obligation.celex,
                    "article_ref": obligation.article_ref,
                },
            )
            if event:
                created += 1
        return created

    def seed_events_from_policy_reviews(self, tenant_id: str) -> int:
        policies = (
            self.db.query(PolicyDocument)
            .filter(
                or_(
                    PolicyDocument.tenant_id == tenant_id,
                    and_(PolicyDocument.tenant_id.is_(None), PolicyDocument.is_master.is_(True)),
                ),
                PolicyDocument.status.in_(["approved", "active", "draft"]),
            )
            .all()
        )

        created = 0
        for policy in policies:
            review_months = 12
            if isinstance(policy.metadata_json, dict):
                raw = policy.metadata_json.get("review_frequency_months")
                if isinstance(raw, int) and raw > 0:
                    review_months = raw
            anchor = (
                policy.last_reviewed_at or policy.effective_date or policy.created_at or utc_now()
            )
            due_date = anchor + timedelta(days=review_months * 30)

            event = self._create_or_update_event(
                tenant_id=tenant_id,
                event_type="policy_review",
                due_date=due_date,
                title=f"Policy review due: {policy.name}",
                description=f"Policy '{policy.policy_id}' requires periodic review.",
                policy_id=policy.id,
                reminder_days_before=30,
                metadata={
                    "policy_id": policy.policy_id,
                    "review_frequency_months": review_months,
                },
            )
            if event:
                created += 1
        return created

    def seed_events_from_kyc_reviews(self, tenant_id: str) -> int:
        profiles = (
            self.db.query(ComplianceProfile)
            .filter(
                ComplianceProfile.tenant_id == tenant_id,
                ComplianceProfile.type == "kyc",
                ComplianceProfile.next_review_date.is_not(None),
                ComplianceProfile.status.in_(["approved", "manual_review", "pending"]),
            )
            .all()
        )

        created = 0
        for profile in profiles:
            event = self._create_or_update_event(
                tenant_id=tenant_id,
                event_type="kyc_review",
                due_date=profile.next_review_date,
                title=f"KYC periodic review: profile {profile.id}",
                description=f"KYC periodic review required for user {profile.user_id or 'unknown'}.",
                compliance_profile_id=profile.id,
                reminder_days_before=7,
                metadata={
                    "user_id": profile.user_id,
                    "cdd_level": profile.cdd_level,
                },
            )
            if event:
                created += 1
        return created

    def propagate_regulatory_change(self, tenant_id: str, doc_id: int) -> int:
        regulation = self.db.query(LegalDocument).filter(LegalDocument.id == doc_id).first()
        if not regulation:
            raise ValueError("Regulation not found")

        obligations = (
            self.db.query(RegulatoryObligation)
            .outerjoin(
                TenantObligationApplicability,
                and_(
                    TenantObligationApplicability.obligation_id == RegulatoryObligation.id,
                    TenantObligationApplicability.tenant_id == tenant_id,
                ),
            )
            .filter(
                RegulatoryObligation.doc_id == doc_id,
                or_(
                    TenantObligationApplicability.id.is_(None),
                    TenantObligationApplicability.applicability.in_(APPLICABLE_OBLIGATION_STATUSES),
                ),
            )
            .all()
        )

        created = 0
        due_date = utc_now() + timedelta(days=7)
        if not obligations:
            event = self._create_or_update_event(
                tenant_id=tenant_id,
                event_type="regulatory_change",
                due_date=due_date,
                title=f"Regulatory change impact analysis: {regulation.celex or regulation.id}",
                description="Assess impact of recent regulatory change on tenant controls.",
                regulation_doc_id=regulation.id,
                reminder_days_before=3,
                metadata={"celex": regulation.celex, "title": regulation.title},
            )
            return 1 if event else 0

        for obligation in obligations:
            event = self._create_or_update_event(
                tenant_id=tenant_id,
                event_type="regulatory_change",
                due_date=due_date,
                title=f"Regulatory change impact: {obligation.obligation_id}",
                description="Validate policy/rule mapping due to regulation update.",
                regulation_doc_id=regulation.id,
                obligation_id=obligation.id,
                policy_id=obligation.linked_policy_id,
                reminder_days_before=3,
                metadata={
                    "celex": regulation.celex,
                    "article_ref": obligation.article_ref,
                },
            )
            if event:
                created += 1
        return created

    def check_overdue_events(self, tenant_id: Optional[str] = None) -> int:
        query = self.db.query(ComplianceCalendarEvent).filter(
            ComplianceCalendarEvent.status.in_(["pending", "acknowledged", "in_progress"]),
            ComplianceCalendarEvent.due_date.is_not(None),
            ComplianceCalendarEvent.due_date < utc_now(),
        )
        if tenant_id:
            query = query.filter(ComplianceCalendarEvent.tenant_id == tenant_id)

        events = query.all()
        for event in events:
            event.status = "overdue"
        return len(events)

    def get_events_requiring_reminders(
        self, tenant_id: Optional[str] = None
    ) -> List[ComplianceCalendarEvent]:
        query = self.db.query(ComplianceCalendarEvent).filter(
            ComplianceCalendarEvent.status.in_(list(ACTIVE_EVENT_STATUSES)),
            ComplianceCalendarEvent.due_date.is_not(None),
        )
        if tenant_id:
            query = query.filter(ComplianceCalendarEvent.tenant_id == tenant_id)

        now = utc_now()
        today = now.date()
        events = query.all()
        due_for_reminder: List[ComplianceCalendarEvent] = []
        for event in events:
            if not event.due_date:
                continue
            days_until_due = (event.due_date.date() - today).days
            threshold = int(event.reminder_days_before or 0)
            already_sent_today = (
                event.last_reminder_at is not None and event.last_reminder_at.date() == today
            )
            if not already_sent_today and days_until_due <= threshold:
                due_for_reminder.append(event)
        return due_for_reminder

    def mark_event_reminded(self, event: ComplianceCalendarEvent) -> None:
        event.last_reminder_at = utc_now()
        event.reminder_count = int(event.reminder_count or 0) + 1

    def update_event_status(
        self,
        *,
        tenant_id: str,
        event_id: int,
        status: str,
        assigned_to: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> ComplianceCalendarEvent:
        event = (
            self.db.query(ComplianceCalendarEvent)
            .filter(
                ComplianceCalendarEvent.id == event_id,
                ComplianceCalendarEvent.tenant_id == tenant_id,
            )
            .first()
        )
        if not event:
            raise ValueError("Event not found")

        normalized = status.lower().strip()
        event.status = normalized
        if assigned_to is not None:
            event.assigned_to = assigned_to
        if priority is not None:
            event.priority = priority
        if normalized == "acknowledged":
            event.acknowledged_at = utc_now()
        if normalized == "completed":
            event.completed_at = utc_now()
        return event

    def _create_or_update_event(
        self,
        *,
        tenant_id: str,
        event_type: str,
        due_date: Optional[datetime],
        title: str,
        description: Optional[str] = None,
        regulation_doc_id: Optional[int] = None,
        obligation_id: Optional[int] = None,
        policy_id: Optional[int] = None,
        compliance_profile_id: Optional[int] = None,
        reminder_days_before: int = 7,
        metadata: Optional[Dict] = None,
    ) -> Optional[ComplianceCalendarEvent]:
        if due_date is None:
            return None

        fingerprint = self._build_fingerprint(
            tenant_id=tenant_id,
            event_type=event_type,
            due_date=due_date,
            regulation_doc_id=regulation_doc_id,
            obligation_id=obligation_id,
            policy_id=policy_id,
            compliance_profile_id=compliance_profile_id,
        )
        existing = (
            self.db.query(ComplianceCalendarEvent)
            .filter(
                ComplianceCalendarEvent.tenant_id == tenant_id,
                ComplianceCalendarEvent.fingerprint == fingerprint,
            )
            .first()
        )
        if existing:
            return None

        event = ComplianceCalendarEvent(
            tenant_id=tenant_id,
            event_type=event_type,
            fingerprint=fingerprint,
            title=title,
            description=description,
            due_date=due_date,
            regulation_doc_id=regulation_doc_id,
            obligation_id=obligation_id,
            policy_id=policy_id,
            compliance_profile_id=compliance_profile_id,
            status="pending",
            priority=self._priority_for_due_date(due_date),
            reminder_days_before=reminder_days_before,
            metadata_json=metadata,
        )
        self.db.add(event)
        self.db.flush()
        return event

    @staticmethod
    def _priority_for_due_date(due_date: datetime) -> str:
        delta_days = (due_date.date() - utc_now().date()).days
        if delta_days <= 7:
            return "high"
        if delta_days <= 30:
            return "medium"
        return "low"

    @staticmethod
    def _build_fingerprint(
        *,
        tenant_id: str,
        event_type: str,
        due_date: datetime,
        regulation_doc_id: Optional[int],
        obligation_id: Optional[int],
        policy_id: Optional[int],
        compliance_profile_id: Optional[int],
    ) -> str:
        raw = (
            f"{tenant_id}:{event_type}:{due_date.date().isoformat()}:"
            f"{regulation_doc_id or ''}:{obligation_id or ''}:"
            f"{policy_id or ''}:{compliance_profile_id or ''}"
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:128]
