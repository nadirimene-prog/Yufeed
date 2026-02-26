import pytest

from src.models.models import LegalDocument, LegalRelation
from src.models.compliance_workflow import RegulatoryObligation
from src.services.obligation_service import (
    normalize_obligations,
    seed_obligations_for_doc,
    mark_related_obligations_for_review,
    get_obligations_needing_review_due_to_relations,
)


@pytest.mark.unit
def test_mark_related_obligations_for_review_uses_to_doc_id(db_session):
    source_doc = LegalDocument(celex="32024R0001", title="Source Regulation")
    target_doc = LegalDocument(celex="32016R0679", title="Target Regulation")
    db_session.add_all([source_doc, target_doc])
    db_session.commit()

    relation = LegalRelation(
        from_doc_id=source_doc.id,
        relation_type="amends",
        to_doc_id=target_doc.id,
    )
    obligation = RegulatoryObligation(
        obligation_id="OBL-REL-001",
        doc_id=target_doc.id,
        celex=target_doc.celex,
        article_ref="Art. 1",
        obligation_text="Maintain controls",
        status="approved",
    )
    db_session.add_all([relation, obligation])
    db_session.commit()

    marked = mark_related_obligations_for_review(db_session, source_doc)
    db_session.refresh(obligation)

    assert marked == 1
    assert obligation.status == "in_review"
    assert "amends" in (obligation.review_notes or "")


@pytest.mark.unit
def test_get_obligations_needing_review_due_to_relations_uses_to_doc_id(db_session):
    source_doc = LegalDocument(celex="32024R0002", title="Source 2")
    target_doc = LegalDocument(celex="32016R0680", title="Target 2")
    db_session.add_all([source_doc, target_doc])
    db_session.commit()

    relation = LegalRelation(
        from_doc_id=source_doc.id,
        relation_type="repeals",
        to_doc_id=target_doc.id,
    )
    obligation = RegulatoryObligation(
        obligation_id="OBL-REL-002",
        doc_id=target_doc.id,
        celex=target_doc.celex,
        article_ref="Art. 2",
        obligation_text="Keep records",
        status="approved",
    )
    db_session.add_all([relation, obligation])
    db_session.commit()

    affected = get_obligations_needing_review_due_to_relations(db_session, source_doc.id)

    assert len(affected) == 1
    assert affected[0]["relation_type"] == "repeals"
    assert affected[0]["source_celex"] == target_doc.celex


@pytest.mark.unit
def test_normalize_obligations_empty_payloads_do_not_create_placeholders():
    assert normalize_obligations(None, "Doc") == []
    assert normalize_obligations([], "Doc") == []
    assert normalize_obligations([{}], "Doc") == []


@pytest.mark.unit
def test_seed_obligations_for_doc_skips_empty_extractions(db_session):
    doc = LegalDocument(
        celex="32024R0101",
        title="Unrelated administrative notice",
        obligations_json=[],
    )
    db_session.add(doc)
    db_session.commit()

    created = seed_obligations_for_doc(db_session, doc, allow_existing=True)

    assert created == 0
    assert (
        db_session.query(RegulatoryObligation).filter(RegulatoryObligation.doc_id == doc.id).count()
        == 0
    )
