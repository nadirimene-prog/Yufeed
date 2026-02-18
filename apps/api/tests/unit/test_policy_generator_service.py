import pytest
from sqlalchemy import text

from src.models.compliance_workflow import (
    InternalRule,
    ObligationPolicyMapping,
    RegulatoryObligation,
)
from src.models.models import LegalDocument
from src.services.policy_generator import (
    GeneratedPolicySection,
    GenerationResult,
    PolicyGenerator,
)


@pytest.mark.unit
def test_approve_generation_returns_monitoring_rule_suggestions(db_session, monkeypatch):
    db_session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS policy_generation_jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT,
                reviewed_by TEXT,
                reviewed_at DATETIME,
                review_notes TEXT,
                final_policy_id INTEGER
            )
            """
        )
    )
    db_session.execute(
        text("INSERT INTO policy_generation_jobs (job_id, status) VALUES ('job-1', 'completed')")
    )
    db_session.commit()

    doc = LegalDocument(
        celex="CELEX-PG-001", title="Policy Generator Regulation", type="regulation"
    )
    db_session.add(doc)
    db_session.flush()

    obligation = RegulatoryObligation(
        obligation_id="OBL-PG-001",
        doc_id=doc.id,
        celex=doc.celex,
        article_ref="Art. 33",
        obligation_text="Transactions above 10,000 EUR must be monitored and reported.",
        status="approved",
    )
    db_session.add(obligation)
    db_session.commit()

    generator = PolicyGenerator(db_session)
    fake_result = GenerationResult(
        job_id="job-1",
        status="completed",
        generated_content="# Generated policy content",
        sections=[GeneratedPolicySection(section_order=1, title="Scope", content="...")],
        summary="summary",
        obligations_covered=[obligation.id],
        variables_used={},
        ai_confidence=0.91,
        word_count=4,
        estimated_reading_time=1,
    )
    monkeypatch.setattr(generator, "get_generation_result", lambda job_id: fake_result)

    approval = generator.approve_generation(job_id="job-1", reviewed_by="tester")
    assert approval["policy_id"] > 0
    assert approval["suggestion_count"] >= 1

    suggestion = approval["suggested_monitoring_rules"][0]
    assert suggestion["obligation_id"] == obligation.id
    assert suggestion["internal_rule_key"].startswith("IR-")
    assert suggestion["status"] in {"suggested", "already_mapped"}
    if suggestion["status"] == "suggested":
        assert suggestion["suggested_monitoring_rule"]["conditions"] is not None

    mapping = (
        db_session.query(ObligationPolicyMapping)
        .filter(
            ObligationPolicyMapping.obligation_id == obligation.id,
            ObligationPolicyMapping.policy_id == approval["policy_id"],
        )
        .first()
    )
    assert mapping is not None

    internal_rule = (
        db_session.query(InternalRule).filter(InternalRule.obligation_id == obligation.id).first()
    )
    assert internal_rule is not None
