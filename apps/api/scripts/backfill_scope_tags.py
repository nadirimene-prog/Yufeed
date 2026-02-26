"""
Backfill scope_tags for LegalDocument and RegulatoryObligation.
"""

from __future__ import annotations

import os
import sys
from typing import Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import SessionLocal
from src.models.models import LegalDocument
from src.models.compliance_workflow import RegulatoryObligation
from src.compliance.scope import infer_scope_tags, normalize_scope_tags


def backfill_scope_tags() -> None:
    db = SessionLocal()
    try:
        docs = db.query(LegalDocument).all()
        doc_updates = 0
        obligation_updates = 0

        for doc in docs:
            existing_doc_scope_tags = normalize_scope_tags(doc.scope_tags)
            inferred_doc_scope_tags = infer_scope_tags(
                doc.title,
                doc.full_text,
                doc.ai_summary,
                doc.obligations_json,
            )
            doc_scope_tags = existing_doc_scope_tags or inferred_doc_scope_tags
            normalized_doc_scope_value = doc_scope_tags or None
            if doc.scope_tags != normalized_doc_scope_value:
                doc.scope_tags = normalized_doc_scope_value
                db.add(doc)
                doc_updates += 1

            obligations = (
                db.query(RegulatoryObligation).filter(RegulatoryObligation.doc_id == doc.id).all()
            )
            for obligation in obligations:
                existing_obligation_scope_tags = normalize_scope_tags(obligation.scope_tags)
                obligation_scope_tags = (
                    existing_obligation_scope_tags
                    or infer_scope_tags(
                        doc.title,
                        doc.full_text,
                        doc.ai_summary,
                        obligation.obligation_text,
                        obligation.applicability,
                    )
                    or doc_scope_tags
                )
                normalized_obligation_scope_value = obligation_scope_tags or None
                if obligation.scope_tags != normalized_obligation_scope_value:
                    obligation.scope_tags = normalized_obligation_scope_value
                    db.add(obligation)
                    obligation_updates += 1

        db.commit()
        print(f"✅ Updated {doc_updates} documents and {obligation_updates} obligations.")
    except Exception as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


if __name__ == "__main__":
    backfill_scope_tags()
