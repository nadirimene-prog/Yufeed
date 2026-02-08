import logging
from datetime import datetime
from typing import Any, List, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from src.models.compliance_workflow import RegulatoryObligation
from src.models.models import LegalDocument, LegalRelation
from src.compliance.scope import infer_scope_tags
from src.utils.time import utc_now

logger = logging.getLogger(__name__)


def _parse_deadline(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def normalize_obligations(raw: Any, fallback_title: str) -> List[dict]:
    if raw is None:
        return [
            {"obligation_text": f"Review obligations for {fallback_title}", "article_ref": None}
        ]

    items: List[Any]
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        for key in ("obligations", "items", "data"):
            if key in raw and isinstance(raw[key], list):
                items = raw[key]
                break
        else:
            items = [raw]
    else:
        items = [raw]

    normalized: List[dict] = []
    for item in items:
        if isinstance(item, dict):
            text = (
                item.get("obligation")
                or item.get("text")
                or item.get("summary")
                or item.get("requirement")
            )
            article = item.get("article") or item.get("article_ref") or item.get("articleRef")
            applicability = item.get("applicability") or item.get("scope")
            deadline = item.get("deadline")
            source_excerpt = item.get("source_excerpt")
        else:
            text = str(item)
            article = None
            applicability = None
            deadline = None
            source_excerpt = None

        normalized.append(
            {
                "obligation_text": text or f"Review obligations for {fallback_title}",
                "article_ref": article,
                "applicability": applicability,
                "deadline": deadline,
                "source_excerpt": source_excerpt,
            }
        )

    if not normalized:
        return [
            {"obligation_text": f"Review obligations for {fallback_title}", "article_ref": None}
        ]

    return normalized


def seed_obligations_for_doc(db: Session, doc: LegalDocument, allow_existing: bool = False) -> int:
    existing_rows = (
        db.query(RegulatoryObligation).filter(RegulatoryObligation.doc_id == doc.id).all()
    )
    if existing_rows and not allow_existing:
        return 0

    existing_keys = {
        (
            (row.obligation_text or "").strip().lower(),
            (row.article_ref or "").strip().lower(),
        )
        for row in existing_rows
    }

    doc_scope_tags = doc.scope_tags or infer_scope_tags(
        doc.title,
        doc.full_text,
        doc.ai_summary,
        doc.obligations_json,
    )
    if doc_scope_tags and doc.scope_tags != doc_scope_tags:
        doc.scope_tags = doc_scope_tags
        db.add(doc)

    items = normalize_obligations(doc.obligations_json, doc.title or "Untitled document")
    created = 0

    for item in items:
        key = (
            (item.get("obligation_text") or "").strip().lower(),
            (item.get("article_ref") or "").strip().lower(),
        )
        if existing_keys and key in existing_keys:
            continue
        evidence = {}
        if item.get("deadline"):
            evidence["deadline"] = item.get("deadline")
        if item.get("source_excerpt"):
            evidence["source_excerpt"] = item.get("source_excerpt")
        evidence = evidence or None

        obligation_scope_tags = (
            infer_scope_tags(
                doc.title,
                doc.full_text,
                doc.ai_summary,
                item.get("obligation_text"),
                item.get("applicability"),
            )
            or doc_scope_tags
        )

        obligation = RegulatoryObligation(
            obligation_id=f"OBL-{uuid4().hex[:10].upper()}",
            doc_id=doc.id,
            celex=getattr(doc, "celex", None),
            article_ref=item.get("article_ref"),
            obligation_text=item.get("obligation_text")
            or doc.title
            or "Review regulatory obligations",
            applicability=item.get("applicability"),
            effective_date=_parse_deadline(item.get("deadline")),
            status="draft",
            evidence_json=evidence,
            scope_tags=obligation_scope_tags,
        )
        db.add(obligation)
        created += 1

    db.commit()
    return created


def mark_related_obligations_for_review(
    db: Session,
    doc: LegalDocument,
    relation_types: Optional[List[str]] = None,
) -> int:
    """
    Mark obligations from related documents for review when a document is amended.

    When a new document amends, repeals, or supersedes an existing document,
    the obligations from the related document should be reviewed to ensure
    they are still current and accurate.

    Args:
        db: Database session
        doc: The newly ingested/updated document
        relation_types: Types of relations to cascade (default: amends, repeals, supersedes)

    Returns:
        Number of obligations marked for review
    """
    if relation_types is None:
        relation_types = ["amends", "repeals", "supersedes", "corrects", "replaces"]

    # Find relations where this document affects other documents
    relations = (
        db.query(LegalRelation)
        .filter(
            LegalRelation.from_doc_id == doc.id,
            LegalRelation.relation_type.in_(relation_types),
        )
        .all()
    )

    if not relations:
        return 0

    marked = 0
    now = utc_now()

    for relation in relations:
        # Find the related document by CELEX
        related_doc = (
            db.query(LegalDocument).filter(LegalDocument.celex == relation.to_celex).first()
        )

        if not related_doc:
            logger.debug(f"Related document {relation.to_celex} not found in database")
            continue

        # Find approved obligations for the related document
        related_obligations = (
            db.query(RegulatoryObligation)
            .filter(
                RegulatoryObligation.doc_id == related_doc.id,
                RegulatoryObligation.status == "approved",
            )
            .all()
        )

        for obl in related_obligations:
            # Mark for review with context about why
            obl.status = "in_review"
            review_note = (
                f"[{now.strftime('%Y-%m-%d')}] Marked for review: "
                f"Related document {doc.celex} ({relation.relation_type}) published. "
                f"Previous status: approved."
            )
            if obl.review_notes:
                obl.review_notes = f"{obl.review_notes}\n{review_note}"
            else:
                obl.review_notes = review_note
            marked += 1
            logger.info(
                f"Marked obligation {obl.obligation_id} for review due to "
                f"{relation.relation_type} from {doc.celex}"
            )

    if marked > 0:
        db.commit()
        logger.info(
            f"Marked {marked} obligations for review due to document relations from {doc.celex}"
        )

    return marked


def get_obligations_needing_review_due_to_relations(
    db: Session,
    doc_id: int,
) -> List[dict]:
    """
    Get list of obligations that might need review based on document relations.

    This is useful for showing users what obligations might be affected
    by a newly ingested document.

    Args:
        db: Database session
        doc_id: ID of the newly ingested document

    Returns:
        List of obligation summaries that might need review
    """
    doc = db.query(LegalDocument).filter(LegalDocument.id == doc_id).first()
    if not doc:
        return []

    # Get relations where this document affects others
    relations = (
        db.query(LegalRelation)
        .filter(
            LegalRelation.from_doc_id == doc_id,
            LegalRelation.relation_type.in_(
                ["amends", "repeals", "supersedes", "corrects", "replaces"]
            ),
        )
        .all()
    )

    affected_obligations = []

    for relation in relations:
        related_doc = (
            db.query(LegalDocument).filter(LegalDocument.celex == relation.to_celex).first()
        )

        if not related_doc:
            continue

        obligations = (
            db.query(RegulatoryObligation)
            .filter(
                RegulatoryObligation.doc_id == related_doc.id,
                RegulatoryObligation.status.in_(["approved", "in_review"]),
            )
            .all()
        )

        for obl in obligations:
            affected_obligations.append(
                {
                    "obligation_id": obl.obligation_id,
                    "obligation_text": (obl.obligation_text or "")[:200],
                    "article_ref": obl.article_ref,
                    "status": obl.status,
                    "affected_by_celex": doc.celex,
                    "affected_by_title": doc.title,
                    "relation_type": relation.relation_type,
                    "source_celex": related_doc.celex,
                    "source_title": related_doc.title,
                }
            )

    return affected_obligations
