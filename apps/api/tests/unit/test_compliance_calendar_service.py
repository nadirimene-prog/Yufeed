import pytest
from datetime import datetime, timedelta, timezone

from src.models.compliance import KYCProfile
from src.models.compliance_calendar import ComplianceCalendarEvent
from src.models.compliance_workflow import PolicyDocument, RegulatoryObligation
from src.models.models import LegalDocument
from src.services.compliance_calendar import ComplianceCalendarService


@pytest.mark.unit
def test_seed_and_deduplicate_calendar_events(db_session):
    now = datetime.now(timezone.utc)
    doc = LegalDocument(celex="CELEX-CAL-001", title="Calendar Regulation", type="regulation")
    db_session.add(doc)
    db_session.flush()

    obligation = RegulatoryObligation(
        obligation_id="OBL-CAL-001",
        doc_id=doc.id,
        celex=doc.celex,
        article_ref="Art. 1",
        obligation_text="Implement monitoring controls",
        effective_date=now + timedelta(days=12),
        status="approved",
    )
    policy = PolicyDocument(
        policy_id="POL-CAL-001",
        tenant_id="default",
        name="Calendar Policy",
        status="approved",
        last_reviewed_at=now - timedelta(days=370),
    )
    profile = KYCProfile(
        tenant_id="default",
        user_id="user-cal-1",
        first_name="Cal",
        last_name="User",
        email="cal.user@example.com",
        status="approved",
        next_review_date=now + timedelta(days=5),
    )
    db_session.add_all([obligation, policy, profile])
    db_session.commit()

    service = ComplianceCalendarService(db_session)
    created_obligations = service.seed_events_from_obligations("default")
    created_policy_reviews = service.seed_events_from_policy_reviews("default")
    created_kyc_reviews = service.seed_events_from_kyc_reviews("default")
    db_session.commit()

    assert created_obligations >= 1
    assert created_policy_reviews >= 1
    assert created_kyc_reviews >= 1

    # Re-seeding should not duplicate due to fingerprint uniqueness logic.
    assert service.seed_events_from_obligations("default") == 0
    assert service.seed_events_from_policy_reviews("default") == 0
    assert service.seed_events_from_kyc_reviews("default") == 0


@pytest.mark.unit
def test_check_overdue_and_reminder_marking(db_session):
    event = ComplianceCalendarEvent(
        tenant_id="default",
        event_type="obligation_deadline",
        fingerprint="cal-overdue-1",
        title="Overdue event",
        due_date=datetime.now(timezone.utc) - timedelta(days=1),
        status="pending",
        reminder_days_before=2,
    )
    db_session.add(event)
    db_session.commit()

    service = ComplianceCalendarService(db_session)
    updated = service.check_overdue_events("default")
    db_session.commit()
    db_session.refresh(event)
    assert updated == 1
    assert event.status == "overdue"

    due = service.get_events_requiring_reminders("default")
    assert any(e.id == event.id for e in due)

    service.mark_event_reminded(event)
    db_session.commit()
    db_session.refresh(event)
    assert event.reminder_count == 1
    assert event.last_reminder_at is not None
