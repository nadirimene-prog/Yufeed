import pytest
from datetime import datetime, timezone

from tests.factories import TransactionFactory, AlertFactory
from src.models.models import LegalDocument
from src.api import cases as cases_api
from src.schemas.transaction_schemas import CaseCreate, CaseUpdate
from src.tenancy.context import set_current_tenant, clear_current_tenant


@pytest.mark.unit
def test_cases_workflow(db_session):
    set_current_tenant("default")
    try:
        tx = TransactionFactory(sqlalchemy_session=db_session)
        alert = AlertFactory(sqlalchemy_session=db_session, transaction=tx)
        regulation = LegalDocument(
            celex="32016R0679",
            title="GDPR",
            publication_date=datetime(2016, 4, 27, tzinfo=timezone.utc),
        )
        db_session.add(regulation)
        db_session.commit()

        case_payload = CaseCreate(
            case_type="investigation",
            subject_type="user",
            subject_id=alert.user_id,
            priority="medium",
            title="Test Case",
            description="Details",
            related_alert_ids=[alert.id],
            related_transaction_ids=[tx.id],
            related_users=[alert.user_id],
            applicable_regulation_ids=[regulation.id],
        )

        created = cases_api.create_case(case_payload, db_session)
        case_id = created.case_id

        cases = cases_api.list_cases(skip=0, limit=100, db=db_session)
        assert any(c.case_id == case_id for c in cases)

        fetched = cases_api.get_case(case_id, db_session, tenant_id="default")
        assert fetched.case_id == case_id

        updated = cases_api.update_case(
            case_id,
            CaseUpdate(summary="updated", priority="high"),
            db_session,
            tenant_id="default",
        )
        assert updated.summary == "updated"

        assigned = cases_api.assign_case(
            case_id,
            assigned_to="analyst@example.com",
            team="compliance",
            db=db_session,
            tenant_id="default",
        )
        assert assigned["assigned_to"] == "analyst@example.com"

        escalated = cases_api.escalate_case(
            case_id,
            escalation_notes="needs review",
            db=db_session,
            tenant_id="default",
        )
        assert escalated["status"] == "escalated"

        closed = cases_api.close_case(
            case_id,
            outcome="resolved",
            outcome_notes="ok",
            db=db_session,
            tenant_id="default",
        )
        assert closed["status"] == "closed"

        alerts = cases_api.get_case_alerts(case_id, db_session, tenant_id="default")
        assert alerts

        transactions = cases_api.get_case_transactions(case_id, db_session, tenant_id="default")
        assert transactions

        setattr(cases_api.LegalDocument, "document_type", property(lambda self: self.type))
        regulations = cases_api.get_case_regulations(case_id, db_session, tenant_id="default")
        assert regulations

        added = cases_api.add_alert_to_case(
            case_id, alert.alert_id, db_session, tenant_id="default"
        )
        assert added["case_id"] == case_id

        evidence = cases_api.add_evidence(
            case_id,
            evidence_key="note",
            evidence_value="evidence",
            db=db_session,
            tenant_id="default",
        )
        assert evidence["case_id"] == case_id

        stats = cases_api.get_case_statistics(db_session)
        assert stats["total_cases"] >= 1
    finally:
        clear_current_tenant()
