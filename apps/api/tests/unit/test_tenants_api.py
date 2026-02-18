import pytest

from src.api import tenants as tenants_api
from src.auth.dependencies import CurrentUser
from src.schemas.tenant_schemas import (
    TenantCreate,
    TenantUpdate,
    TenantConfigUpdate,
    RateLimitConfig,
    FeatureFlagConfig,
    TenantSettings,
    APIKeyCreate,
    APIKeyUpdate,
    TenantUserCreate,
    TenantRegulatoryProfileUpdate,
    TenantRegulationAssignment,
)
from src.models.tenant_models import Tenant, TenantAPIKey, TenantUser
from src.models.models import LegalDocument


@pytest.mark.unit
def test_tenant_lifecycle_and_api_keys(db_session):
    current_user = CurrentUser(
        user_id="superuser",
        email="superuser@example.com",
        role="admin",
        tenant_id=None,
        is_superuser=True,
    )

    tenant_payload = TenantCreate(
        tenant_id="acme_test",
        name="Acme Corp",
        contact_email="ops@acme.test",
        tier="standard",
    )
    tenant = tenants_api.create_tenant(tenant_payload, db_session, current_user=current_user)
    assert tenant.tenant_id == "acme_test"

    tenants = tenants_api.list_tenants(skip=0, limit=100, db=db_session, current_user=current_user)
    assert any(t.tenant_id == "acme_test" for t in tenants)

    fetched = tenants_api.get_tenant("acme_test", db_session, current_user=current_user)
    assert fetched.name == "Acme Corp"

    updated = tenants_api.update_tenant(
        "acme_test",
        TenantUpdate(name="Acme Updated"),
        db_session,
        current_user=current_user,
    )
    assert updated.name == "Acme Updated"

    config_update = TenantConfigUpdate(
        settings=TenantSettings(timezone="UTC"),
        rate_limits=RateLimitConfig(requests_per_minute=10),
        feature_flags=FeatureFlagConfig(ml_auto_triage=False),
    )
    updated = tenants_api.update_tenant_config(
        "acme_test",
        config_update,
        db_session,
        current_user=current_user,
    )
    assert updated.settings["timezone"] == "UTC"

    stats = tenants_api.get_tenant_stats("acme_test", db_session, current_user=current_user)
    assert stats.tenant_id == "acme_test"

    created_key = tenants_api.create_api_key(
        "acme_test",
        APIKeyCreate(name="Primary Key", description="test", scopes=["read"]),
        db_session,
        current_user=current_user,
    )
    assert created_key.api_key.startswith("yk_live_acme_test_")

    key_id = created_key.id
    keys = tenants_api.list_api_keys(
        "acme_test",
        include_revoked=False,
        db=db_session,
        current_user=current_user,
    )
    assert any(k.id == key_id for k in keys)

    updated_key = tenants_api.update_api_key(
        "acme_test",
        key_id,
        APIKeyUpdate(name="Rotatable", scopes=["read", "write"]),
        db_session,
        current_user=current_user,
    )
    assert updated_key.name == "Rotatable"

    rotated = tenants_api.rotate_api_key("acme_test", key_id, db_session, current_user=current_user)
    assert rotated.old_key_id == key_id
    assert rotated.new_key.api_key.startswith("yk_live_acme_test_")

    new_key_id = rotated.new_key.id
    tenants_api.revoke_api_key("acme_test", new_key_id, db_session, current_user=current_user)
    revoked = db_session.query(TenantAPIKey).filter(TenantAPIKey.id == new_key_id).first()
    assert revoked.revoked_at is not None

    user = tenants_api.add_user_to_tenant(
        "acme_test",
        TenantUserCreate(user_id="user_1", role="admin"),
        db_session,
        current_user=current_user,
    )
    assert user.user_id == "user_1"

    users = tenants_api.list_tenant_users(
        "acme_test",
        is_active=None,
        db=db_session,
        current_user=current_user,
    )
    assert any(u.user_id == "user_1" for u in users)

    tenants_api.remove_user_from_tenant(
        "acme_test",
        "user_1",
        db_session,
        current_user=current_user,
    )
    remaining = db_session.query(TenantUser).filter(TenantUser.user_id == "user_1").first()
    assert remaining is None

    tenants_api.delete_tenant(
        "acme_test", hard_delete=False, db=db_session, current_user=current_user
    )
    deleted = db_session.query(Tenant).filter(Tenant.tenant_id == "acme_test").first()
    assert deleted.is_active is False


@pytest.mark.unit
def test_tenant_regulatory_profile_and_applicable_regulations(db_session):
    current_user = CurrentUser(
        user_id="superuser",
        email="superuser@example.com",
        role="admin",
        tenant_id=None,
        is_superuser=True,
    )

    tenant = tenants_api.create_tenant(
        TenantCreate(
            tenant_id="regtech_tenant",
            name="RegTech Tenant",
            tier="enterprise",
        ),
        db_session,
        current_user=current_user,
    )
    assert tenant.tenant_id == "regtech_tenant"

    psp_doc = LegalDocument(
        celex="32023R1111",
        title="Payment Services Framework",
        scope_tags=["psp"],
    )
    vasp_doc = LegalDocument(
        celex="32023R2222",
        title="Crypto Asset Framework",
        scope_tags=["vasp"],
    )
    db_session.add_all([psp_doc, vasp_doc])
    db_session.commit()

    updated = tenants_api.update_tenant_regulatory_profile(
        "regtech_tenant",
        TenantRegulatoryProfileUpdate(
            institution_type="pi",
            license_jurisdiction="fr",
            supervisory_authority="ACPR",
        ),
        db_session,
        current_user=current_user,
    )
    assert updated.institution_type == "pi"
    assert updated.license_jurisdiction == "FR"

    applicable = tenants_api.get_applicable_regulations(
        "regtech_tenant",
        include_exempt=False,
        db=db_session,
        current_user=current_user,
    )
    applicable_ids = {entry["regulation_doc_id"] for entry in applicable}
    assert psp_doc.id in applicable_ids
    assert vasp_doc.id not in applicable_ids

    assignment = tenants_api.upsert_tenant_regulation_applicability(
        "regtech_tenant",
        TenantRegulationAssignment(
            regulation_doc_id=vasp_doc.id,
            applicability="partial",
            applicability_notes="Crypto pilot activity",
        ),
        db_session,
        current_user=current_user,
    )
    assert assignment.created is True
    assert assignment.applicability == "partial"

    applicable_after_override = tenants_api.get_applicable_regulations(
        "regtech_tenant",
        include_exempt=False,
        db=db_session,
        current_user=current_user,
    )
    overridden_ids = {entry["regulation_doc_id"] for entry in applicable_after_override}
    assert vasp_doc.id in overridden_ids

    removed = tenants_api.upsert_tenant_regulation_applicability(
        "regtech_tenant",
        TenantRegulationAssignment(
            regulation_doc_id=vasp_doc.id,
            remove=True,
        ),
        db_session,
        current_user=current_user,
    )
    assert removed.removed is True

    applicable_after_remove = tenants_api.get_applicable_regulations(
        "regtech_tenant",
        include_exempt=False,
        db=db_session,
        current_user=current_user,
    )
    removed_ids = {entry["regulation_doc_id"] for entry in applicable_after_remove}
    assert vasp_doc.id not in removed_ids
