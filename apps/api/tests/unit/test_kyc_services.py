import pytest
from datetime import datetime, timedelta, timezone

from src.models.compliance import KYCProfile, ComplianceStatus
from src.models.finding_models import Finding
from src.services.kyc_finding_bridge import KYCFindingBridge
from src.services.kyc_onboarding import KYCOnboardingService
from src.services.kyc_periodic_review import KYCPeriodicReviewService


@pytest.mark.unit
def test_determine_cdd_level_escalates_for_pep(db_session):
    profile = KYCProfile(
        tenant_id="default",
        first_name="Jane",
        last_name="Doe",
        email="jane.doe@example.com",
        pep_status="pep",
        risk_level="low",
        status=ComplianceStatus.PENDING.value,
    )
    db_session.add(profile)
    db_session.commit()

    service = KYCOnboardingService(db_session)
    level = service.determine_cdd_level(profile_id=profile.id, tenant_id="default")
    db_session.commit()
    db_session.refresh(profile)

    assert level == "enhanced"
    assert profile.cdd_level == "enhanced"
    assert profile.review_frequency_months == 6
    assert profile.next_review_date is not None


@pytest.mark.unit
def test_periodic_review_finds_due_profiles(db_session):
    due_profile = KYCProfile(
        tenant_id="default",
        first_name="Due",
        last_name="User",
        email="due.user@example.com",
        status=ComplianceStatus.APPROVED.value,
        next_review_date=datetime.now(timezone.utc) - timedelta(days=2),
    )
    future_profile = KYCProfile(
        tenant_id="default",
        first_name="Future",
        last_name="User",
        email="future.user@example.com",
        status=ComplianceStatus.APPROVED.value,
        next_review_date=datetime.now(timezone.utc) + timedelta(days=10),
    )
    db_session.add_all([due_profile, future_profile])
    db_session.commit()

    service = KYCPeriodicReviewService(db_session)
    due = service.find_profiles_due_for_review(tenant_id="default")
    assert any(profile.id == due_profile.id for profile in due)
    assert all(profile.id != future_profile.id for profile in due)

    reviewed = service.initiate_review(profile_id=due_profile.id, tenant_id="default")
    db_session.commit()
    assert reviewed.status == ComplianceStatus.MANUAL_REVIEW.value


@pytest.mark.unit
def test_kyc_finding_bridge_creates_and_deduplicates(db_session):
    bridge = KYCFindingBridge(db_session)

    finding, is_new = bridge.create_kyc_failure(
        tenant_id="default",
        profile_id=123,
        user_id="user-1",
        reason="Missing identity document",
        details={"document_type": "passport"},
    )
    db_session.commit()

    assert is_new is True
    assert finding.finding_type == "KYC_FAILURE"

    finding_2, is_new_2 = bridge.create_kyc_failure(
        tenant_id="default",
        profile_id=123,
        user_id="user-1",
        reason="Missing identity document",
        details={"document_type": "passport"},
    )
    db_session.commit()

    assert finding_2.id == finding.id
    assert is_new_2 is False
    assert db_session.query(Finding).filter(Finding.finding_type == "KYC_FAILURE").count() == 1
