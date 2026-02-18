from datetime import datetime, timedelta, timezone

from src.models.compliance import KYCProfile
from src.models.compliance_workflow import PolicyDocument, RegulatoryObligation
from src.models.models import LegalDocument


def _seed_calendar_entities(db_session):
    now = datetime.now(timezone.utc)
    doc = LegalDocument(
        celex="CELEX-CAL-API-001", title="Calendar API Regulation", type="regulation"
    )
    db_session.add(doc)
    db_session.flush()

    obligation = RegulatoryObligation(
        obligation_id="OBL-CAL-API-001",
        doc_id=doc.id,
        celex=doc.celex,
        article_ref="Art. 11",
        obligation_text="API seeded obligation",
        effective_date=now + timedelta(days=20),
        status="approved",
    )
    policy = PolicyDocument(
        policy_id="POL-CAL-API-001",
        tenant_id="default",
        name="API Calendar Policy",
        status="approved",
        last_reviewed_at=now - timedelta(days=380),
    )
    profile = KYCProfile(
        tenant_id="default",
        user_id="user-calendar-api",
        first_name="Api",
        last_name="User",
        email="api.calendar@example.com",
        status="approved",
        next_review_date=now + timedelta(days=10),
    )
    db_session.add_all([obligation, policy, profile])
    db_session.commit()
    return {"doc_id": doc.id}


def test_seed_and_list_compliance_calendar_events(client, db_session, admin_headers):
    _seed_calendar_entities(db_session)

    seed_resp = client.post(
        "/api/compliance-calendar/seed",
        json={
            "include_obligations": True,
            "include_policy_reviews": True,
            "include_kyc_reviews": True,
        },
        headers=admin_headers,
    )
    assert seed_resp.status_code == 200
    payload = seed_resp.json()
    assert payload["tenant_id"] == "default"
    assert payload["total_created"] >= 3

    list_resp = client.get("/api/compliance-calendar/events", headers=admin_headers)
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["total"] >= 3

    event_types = {item["event_type"] for item in data["items"]}
    assert "obligation_deadline" in event_types
    assert "policy_review" in event_types
    assert "kyc_review" in event_types

    first_event_id = data["items"][0]["id"]
    patch_resp = client.patch(
        f"/api/compliance-calendar/events/{first_event_id}",
        json={"status": "acknowledged", "assigned_to": "compliance@example.com"},
        headers=admin_headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "acknowledged"
    assert patch_resp.json()["assigned_to"] == "compliance@example.com"


def test_propagate_regulatory_change_calendar_event(client, db_session, admin_headers):
    seeded = _seed_calendar_entities(db_session)

    response = client.post(
        f"/api/compliance-calendar/regulatory-change/{seeded['doc_id']}",
        headers=admin_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["tenant_id"] == "default"
    assert payload["regulation_doc_id"] == seeded["doc_id"]
    assert payload["created_events"] >= 1

    events_resp = client.get(
        "/api/compliance-calendar/events",
        params={"event_type": "regulatory_change"},
        headers=admin_headers,
    )
    assert events_resp.status_code == 200
    assert events_resp.json()["total"] >= 1
