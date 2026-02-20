import logging
from datetime import datetime
from typing import Any, List, Optional
from uuid import uuid4
import hashlib

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.models.compliance_workflow import RegulatoryObligation, SupervisoryAlert
from src.models.models import LegalDocument, LegalRelation
from src.compliance.scope import infer_scope_tags
from src.utils.time import utc_now
from src.monitoring.metrics import obligations_created_total
from src.ai.analyzer import extract_obligations

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


def _normalize_text(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def _obligation_dedup_hash(obligation_text: Optional[str], article_ref: Optional[str]) -> str:
    canonical = f"{_normalize_text(obligation_text)}|{_normalize_text(article_ref)}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _confidence_tier_for_doc(doc: LegalDocument) -> str:
    if doc.analyzed_at:
        return "high"
    if doc.full_text:
        return "medium"
    return "low"


def _record_obligations_created_metric(source: str, confidence_tier: str, created: int) -> None:
    if created <= 0:
        return
    try:
        obligations_created_total.labels(
            source=(source or "unknown"),
            confidence_tier=(confidence_tier or "unknown"),
        ).inc(created)
    except Exception:
        pass


def seed_obligations_for_doc(
    db: Session,
    doc: LegalDocument,
    allow_existing: bool = False,
    source: Optional[str] = None,
) -> int:
    existing_rows = (
        db.query(RegulatoryObligation).filter(RegulatoryObligation.doc_id == doc.id).all()
    )
    if existing_rows and not allow_existing:
        return 0

    existing_keys = set()
    existing_hashes = set()
    for row in existing_rows:
        existing_keys.add((_normalize_text(row.obligation_text), _normalize_text(row.article_ref)))
        if row.dedup_hash:
            existing_hashes.add(row.dedup_hash)

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
            _normalize_text(item.get("obligation_text")),
            _normalize_text(item.get("article_ref")),
        )
        dedup_hash = _obligation_dedup_hash(item.get("obligation_text"), item.get("article_ref"))
        if key in existing_keys or dedup_hash in existing_hashes:
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
            dedup_hash=dedup_hash,
        )
        try:
            with db.begin_nested():
                db.add(obligation)
                db.flush()
            created += 1
            existing_keys.add(key)
            existing_hashes.add(dedup_hash)
        except IntegrityError:
            continue

    db.commit()
    source_key = source or getattr(doc, "source_system", None) or "unknown"
    confidence_tier = _confidence_tier_for_doc(doc)
    _record_obligations_created_metric(source_key, confidence_tier, created)

    if created > 0:
        try:
            from src.worker import notify_obligations_extracted, auto_map_obligation_policies

            notify_obligations_extracted.delay(doc.id, created, source_key)
            auto_map_obligation_policies.delay(doc.id, source_key)
        except Exception:
            logger.debug("Failed to dispatch async obligation follow-up tasks", exc_info=True)
    return created


def _synthetic_supervisory_celex(alert: SupervisoryAlert) -> str:
    source = (alert.source_system or "SUP").upper()
    published = alert.published_at or utc_now()
    date_part = published.strftime("%Y%m%d")
    digest = hashlib.sha256((alert.dedup_key or str(alert.id)).encode("utf-8")).hexdigest()[:16]
    return f"SUP-{source}-{date_part}-{digest.upper()}"


def _get_or_create_proxy_document_for_alert(db: Session, alert: SupervisoryAlert) -> LegalDocument:
    if alert.legal_doc_id:
        existing = db.query(LegalDocument).filter(LegalDocument.id == alert.legal_doc_id).first()
        if existing:
            return existing

    synthetic_celex = _synthetic_supervisory_celex(alert)
    doc = db.query(LegalDocument).filter(LegalDocument.celex == synthetic_celex).first()
    if doc:
        if alert.legal_doc_id != doc.id:
            alert.legal_doc_id = doc.id
            alert.updated_at = utc_now()
            db.add(alert)
            db.commit()
        return doc

    full_text = f"{alert.title or ''}\n\n{alert.description or ''}".strip() or (
        alert.title or "Supervisory alert"
    )
    doc = LegalDocument(
        celex=synthetic_celex,
        source_system=alert.source_system,
        source_reference=alert.link or f"supervisory:{alert.id}",
        jurisdiction=alert.jurisdiction,
        primary_language=(alert.language or "en").lower(),
        title=alert.title or f"{(alert.source_system or 'supervisory').upper()} alert",
        type="other",
        publication_date=alert.published_at or utc_now(),
        status="active",
        last_modified=utc_now(),
        full_text=full_text,
    )
    db.add(doc)
    db.flush()

    alert.legal_doc_id = doc.id
    alert.updated_at = utc_now()
    db.add(alert)
    db.commit()
    db.refresh(doc)
    return doc


def extract_obligations_from_alert(db: Session, alert: SupervisoryAlert) -> int:
    """
    Extract and seed obligations from a persisted supervisory alert.

    Keeps compatibility with existing obligation APIs by writing into a
    deterministic proxy LegalDocument.
    """
    doc = _get_or_create_proxy_document_for_alert(db, alert)
    raw_obligations = extract_obligations(
        title=alert.title or doc.title,
        celex=doc.celex,
        full_text=f"{alert.title or ''}\n\n{alert.description or ''}".strip(),
        article_breakdown=None,
    )
    doc.obligations_json = raw_obligations
    doc.last_modified = utc_now()
    db.add(doc)
    db.commit()
    db.refresh(doc)

    created = seed_obligations_for_doc(
        db,
        doc,
        allow_existing=True,
        source=alert.source_system or "supervisory",
    )
    if created > 0:
        rows = (
            db.query(RegulatoryObligation)
            .filter(
                RegulatoryObligation.doc_id == doc.id,
                RegulatoryObligation.supervisory_alert_id.is_(None),
            )
            .all()
        )
        for row in rows:
            row.supervisory_alert_id = alert.id
            row.updated_at = utc_now()
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
        # Find the related target document
        related_doc = db.query(LegalDocument).filter(LegalDocument.id == relation.to_doc_id).first()

        if not related_doc:
            logger.debug(
                "Related target document %s not found in database",
                relation.to_doc_id,
            )
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
        related_doc = db.query(LegalDocument).filter(LegalDocument.id == relation.to_doc_id).first()

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
