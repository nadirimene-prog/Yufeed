from datetime import datetime
from typing import Any, List, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from src.models.compliance_workflow import RegulatoryObligation
from src.models.models import LegalDocument
from src.compliance.scope import infer_scope_tags


def _parse_deadline(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def normalize_obligations(raw: Any, fallback_title: str) -> List[dict]:
    if raw is None:
        return [{"obligation_text": f"Review obligations for {fallback_title}", "article_ref": None}]

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
            text = item.get("obligation") or item.get("text") or item.get("summary") or item.get("requirement")
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
        return [{"obligation_text": f"Review obligations for {fallback_title}", "article_ref": None}]

    return normalized


def seed_obligations_for_doc(db: Session, doc: LegalDocument, allow_existing: bool = False) -> int:
    existing_rows = db.query(RegulatoryObligation).filter(
        RegulatoryObligation.doc_id == doc.id
    ).all()
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

        obligation_scope_tags = infer_scope_tags(
            doc.title,
            doc.full_text,
            doc.ai_summary,
            item.get("obligation_text"),
            item.get("applicability"),
        ) or doc_scope_tags

        obligation = RegulatoryObligation(
            obligation_id=f"OBL-{uuid4().hex[:10].upper()}",
            doc_id=doc.id,
            celex=getattr(doc, "celex", None),
            article_ref=item.get("article_ref"),
            obligation_text=item.get("obligation_text") or doc.title or "Review regulatory obligations",
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
