import pytest
from datetime import datetime, timezone
from decimal import Decimal

from src.models.compliance import KYCProfile
from src.models.finding_models import Finding
from src.models.transaction_models import Transaction, UserRiskProfile
from src.services.customer_lifecycle import CustomerLifecycleService


@pytest.mark.unit
def test_sync_kyc_to_risk_profile_and_trigger_edd(db_session):
    profile = KYCProfile(
        tenant_id="default",
        user_id="user-lifecycle-1",
        first_name="Lifecycle",
        last_name="User",
        email="lifecycle.user@example.com",
        status="approved",
        cdd_level="standard",
        pep_status="not_pep",
        sanctions_status="clear",
    )
    db_session.add(profile)

    risk_profile = UserRiskProfile(
        tenant_id="default",
        user_id="user-lifecycle-1",
    )
    db_session.add(risk_profile)
    db_session.flush()

    transaction = Transaction(
        tenant_id="default",
        transaction_id="txn-lifecycle-1",
        user_id="user-lifecycle-1",
        amount=Decimal("15000"),
        currency="EUR",
        transaction_type="transfer",
        timestamp=datetime.now(timezone.utc),
        risk_score=Decimal("90"),
        risk_level="critical",
    )
    db_session.add(transaction)
    db_session.commit()

    service = CustomerLifecycleService(db_session)
    synced_profile = service.sync_kyc_to_risk_profile("user-lifecycle-1", "default")
    assert synced_profile is not None
    assert synced_profile.compliance_profile_id == profile.id
    assert synced_profile.kyc_status == "approved"
    assert synced_profile.kyc_cdd_level == "standard"

    result = service.trigger_edd_from_transactions(transaction.id, "default")
    db_session.commit()

    assert result["triggered"] is True
    db_session.refresh(profile)
    db_session.refresh(risk_profile)
    assert risk_profile.enhanced_due_diligence is True
    assert profile.cdd_level == "enhanced"

    finding = (
        db_session.query(Finding)
        .filter(
            Finding.tenant_id == "default",
            Finding.finding_type == "EDD_TRIGGER",
        )
        .first()
    )
    assert finding is not None
