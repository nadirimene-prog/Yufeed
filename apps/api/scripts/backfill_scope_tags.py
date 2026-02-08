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
from src.compliance.scope import infer_scope_tags


def backfill_scope_tags() -> None:
    db = SessionLocal()
    try:
        docs = db.query(LegalDocument).all()
        doc_updates = 0
        obligation_updates = 0

        for doc in docs:
            doc_scope_tags = doc.scope_tags or infer_scope_tags(
                doc.title,
                doc.full_text,
                doc.ai_summary,
                doc.obligations_json,
            )
            if doc_scope_tags and doc.scope_tags != doc_scope_tags:
                doc.scope_tags = doc_scope_tags
                db.add(doc)
                doc_updates += 1

            obligations = (
                db.query(RegulatoryObligation).filter(RegulatoryObligation.doc_id == doc.id).all()
            )
            for obligation in obligations:
                obligation_scope_tags = (
                    obligation.scope_tags
                    or infer_scope_tags(
                        doc.title,
                        doc.full_text,
                        doc.ai_summary,
                        obligation.obligation_text,
                        obligation.applicability,
                    )
                    or doc_scope_tags
                )
                if obligation_scope_tags and obligation.scope_tags != obligation_scope_tags:
                    obligation.scope_tags = obligation_scope_tags
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
