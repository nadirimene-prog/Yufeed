"""
Seed RegulatoryObligation rows from existing LegalDocument records.
- Uses obligations_json when available
- Falls back to a single placeholder obligation per document
"""

from __future__ import annotations

import argparse
from typing import Any, Iterable, List, Optional
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from uuid import uuid4

from src.database import SessionLocal
from src.models.models import LegalDocument
from src.models.compliance_workflow import RegulatoryObligation
from src.compliance.scope import infer_scope_tags


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        # Common shapes from AI outputs
        for key in ("obligations", "items", "data"):
            if key in value and isinstance(value[key], list):
                return value[key]
        return [value]
    return [value]


def _obligation_text(item: Any, fallback: str) -> str:
    if isinstance(item, dict):
        for key in ("obligation", "text", "summary", "requirement"):
            value = item.get(key)
            if value:
                return str(value)
    if isinstance(item, str):
        return item
    return fallback


def _article_ref(item: Any) -> Optional[str]:
    if isinstance(item, dict):
        for key in ("article", "article_ref", "articleRef"):
            value = item.get(key)
            if value:
                return str(value)
    return None


def seed_obligations(*, allow_placeholder: bool = False) -> None:
    db = SessionLocal()
    try:
        documents = db.query(LegalDocument).all()
        created = 0
        skipped_existing = 0
        skipped_no_extracted = 0

        for doc in documents:
            existing = (
                db.query(RegulatoryObligation).filter(RegulatoryObligation.doc_id == doc.id).count()
            )
            if existing:
                skipped_existing += 1
                continue

            doc_scope_tags = doc.scope_tags or infer_scope_tags(
                doc.title,
                doc.full_text,
                doc.ai_summary,
                doc.obligations_json,
            )
            if doc_scope_tags and doc.scope_tags != doc_scope_tags:
                doc.scope_tags = doc_scope_tags
                db.add(doc)

            obligations = _as_list(getattr(doc, "obligations_json", None))
            if not obligations:
                if not allow_placeholder:
                    skipped_no_extracted += 1
                    continue
                obligations = [
                    {
                        "obligation": f"Review and implement requirements for {doc.title}",
                        "article": None,
                    }
                ]

            for item in obligations:
                obligation_scope_tags = (
                    infer_scope_tags(
                        doc.title,
                        doc.full_text,
                        doc.ai_summary,
                        _obligation_text(item, doc.title or "Obligation"),
                        _article_ref(item),
                    )
                    or doc_scope_tags
                )
                obligation = RegulatoryObligation(
                    obligation_id=f"OBL-{uuid4().hex[:10].upper()}",
                    doc_id=doc.id,
                    celex=getattr(doc, "celex", None),
                    article_ref=_article_ref(item),
                    obligation_text=_obligation_text(item, doc.title),
                    status="draft",
                    scope_tags=obligation_scope_tags,
                )
                db.add(obligation)
                created += 1

        db.commit()
        print(
            "✅ Seeded "
            f"{created} obligations. "
            f"Skipped {skipped_existing} documents with existing obligations. "
            f"Skipped {skipped_no_extracted} documents with no extracted obligations."
        )
    except Exception as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed RegulatoryObligation rows from LegalDocument records"
    )
    parser.add_argument(
        "--allow-placeholder",
        action="store_true",
        help="Create placeholder obligations when documents have no extracted obligations_json",
    )
    args = parser.parse_args()
    seed_obligations(allow_placeholder=args.allow_placeholder)
