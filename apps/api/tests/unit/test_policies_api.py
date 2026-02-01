import pytest
from datetime import datetime, timezone

from src.api import policies as policies_api
from src.auth.dependencies import CurrentUser
from src.models.compliance_workflow import PolicyDocument, PolicySection, RegulatoryObligation
from src.schemas.policy_schemas import (
    PolicyCreate,
    PolicyUpdate,
    PolicyApprove,
    PolicySectionCreate,
    PolicySectionUpdate,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_policy_crud_and_sections(db_session, monkeypatch):
    async def dummy_broadcast(*args, **kwargs):
        return None

    monkeypatch.setattr(policies_api.ws_manager, "broadcast", dummy_broadcast)

    current_user = CurrentUser("user-1", "user@example.com", "admin")

    created = await policies_api.create_policy(
        PolicyCreate(
            name="AML Policy",
            version="1.0",
            owner="compliance",
            status="draft",
            language="en",
            content="Policy content",
            metadata={"owner": "test"},
        ),
        db_session,
        current_user,
    )
    assert created["name"] == "AML Policy"

    listing = policies_api.list_policies(
        status="draft",
        owner="compliance",
        q="AML",
        skip=0,
        limit=50,
        db=db_session,
        _=None,
    )
    assert listing["total"] >= 1

    policy_id = created["id"]

    fetched = policies_api.get_policy(policy_id, db_session, None)
    assert fetched["policy_id"]

    updated = policies_api.update_policy(
        policy_id,
        PolicyUpdate(status="in_review", metadata={"updated": True}),
        db_session,
        current_user,
    )
    assert updated["status"] == "in_review"

    approved = await policies_api.approve_policy(
        policy_id,
        PolicyApprove(note="Approved"),
        db_session,
        current_user,
    )
    assert approved["status"] == "approved"

    # Attach obligation for list_policy_obligations
    from src.models.models import LegalDocument
    doc = LegalDocument(
        celex="32024R8888",
        title="Policy doc",
        jurisdiction="EU",
    )
    db_session.add(doc)
    db_session.commit()
    obligation = RegulatoryObligation(
        obligation_id="OBL-POL",
        document=doc,
        obligation_text="Policy obligation",
        status="approved",
        linked_policy_id=policy_id,
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(obligation)
    db_session.commit()

    obligations = policies_api.list_policy_obligations(policy_id, 0, 50, db_session, None)
    assert obligations["items"]

    section = policies_api.create_policy_section(
        policy_id,
        PolicySectionCreate(section_ref="1", title="Intro", content="Intro", status="draft"),
        db_session,
        current_user,
    )
    assert section["section_ref"] == "1"

    sections = policies_api.list_policy_sections(policy_id, db_session, None)
    assert sections["items"]

    updated_section = policies_api.update_policy_section(
        section["id"],
        PolicySectionUpdate(title="Updated"),
        db_session,
        current_user,
    )
    assert updated_section["title"] == "Updated"

    delete_section = policies_api.delete_policy_section(section["id"], db_session, current_user)
    assert delete_section["message"] == "Section deleted"

    with pytest.raises(Exception):
        policies_api.delete_policy(policy_id, db_session, current_user)

    # Remove linked obligations then delete policy
    db_session.query(RegulatoryObligation).filter(
        RegulatoryObligation.linked_policy_id == policy_id
    ).delete()
    db_session.commit()

    delete_policy = policies_api.delete_policy(policy_id, db_session, current_user)
    assert delete_policy["message"] == "Policy deleted"
