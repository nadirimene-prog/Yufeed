import pytest
from datetime import datetime

from sqlalchemy import text

from src.auth.dependencies import CurrentUser
from src.api import policy_generator as policy_generator_api
from src.api import gap_analysis as gap_analysis_api
from src.models.models import LegalDocument
from src.models.compliance_workflow import RegulatoryObligation


class _DummyResult:
    def fetchone(self):
        return (1, 1, 1, 0, 0, 0.9, 1)


class _DummyDB:
    def __init__(self):
        self.params = None

    def execute(self, _query, params):
        self.params = params
        return _DummyResult()


@pytest.mark.unit
def test_policy_generator_stats_uses_timedelta_window():
    db = _DummyDB()
    user = CurrentUser(
        user_id="u-1",
        email="admin@example.com",
        role="admin",
        tenant_id="default",
    )

    stats = policy_generator_api.get_generator_stats(days=40, current_user=user, db=db)

    assert stats["period_days"] == 40
    assert isinstance(db.params["since"], datetime)


@pytest.mark.unit
def test_gap_analysis_obligation_coverage_derived_without_model_fields(db_session):
    db_session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS obligation_policy_mappings (
                id INTEGER PRIMARY KEY,
                obligation_id INTEGER NOT NULL,
                policy_id INTEGER NOT NULL,
                mapping_confidence FLOAT,
                mapped_by TEXT,
                mapped_at DATETIME
            )
            """
        )
    )
    db_session.commit()

    doc = LegalDocument(celex="32024R0300", title="Gap API Document")
    db_session.add(doc)
    db_session.commit()

    obligation = RegulatoryObligation(
        obligation_id="OBL-GAP-001",
        doc_id=doc.id,
        celex=doc.celex,
        article_ref="Art. 5",
        obligation_text="Perform customer due diligence checks",
        status="approved",
    )
    db_session.add(obligation)
    db_session.commit()

    user = CurrentUser(
        user_id="u-2",
        email="compliance@example.com",
        role="compliance",
        tenant_id="default",
    )

    coverage = gap_analysis_api.get_obligation_coverage(
        obligation_id=obligation.id,
        current_user=user,
        db=db_session,
    )

    assert coverage["obligation"]["coverage_status"] == "uncovered"
    assert coverage["obligation"]["category"]
    assert coverage["obligation"]["severity"]
