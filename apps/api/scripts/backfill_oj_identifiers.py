"""Backfill OJ act identifiers on existing legal documents."""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, date
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import SessionLocal
from src.models.models import LegalDocument
from src.models.compliance_workflow import OfficialJournalAct
from src.ingestion.oj_mapping import extract_oj_act_identifier, extract_oj_series


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    return date.fromisoformat(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill OJ act identifiers on legal documents.")
    parser.add_argument("--source-system", default="eur-lex", help="Filter by source_system")
    parser.add_argument("--jurisdiction", default="EU", help="Filter by jurisdiction")
    parser.add_argument("--from-date", default=None, help="Filter publication_date >= YYYY-MM-DD")
    parser.add_argument("--to-date", default=None, help="Filter publication_date <= YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=2000, help="Max documents to scan")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing")
    args = parser.parse_args()

    from_date = _parse_date(args.from_date)
    to_date = _parse_date(args.to_date)

    db = SessionLocal()
    try:
        query = db.query(LegalDocument)
        if args.source_system:
            query = query.filter(LegalDocument.source_system == args.source_system)
        if args.jurisdiction:
            query = query.filter(LegalDocument.jurisdiction == args.jurisdiction)
        query = query.filter(
            (LegalDocument.oj_act_identifier.is_(None))
            | (LegalDocument.oj_signature_identifier.is_(None))
        )
        if from_date:
            query = query.filter(LegalDocument.publication_date >= from_date)
        if to_date:
            query = query.filter(LegalDocument.publication_date <= to_date)

        docs = query.order_by(LegalDocument.publication_date.asc()).limit(args.limit).all()

        seen = 0
        updated = 0
        for doc in docs:
            seen += 1
            source_reference = doc.source_reference or ""
            act_identifier = doc.oj_act_identifier
            signature_identifier = doc.oj_signature_identifier

            if not act_identifier:
                act_identifier = extract_oj_act_identifier(source_reference)

            record = None
            if act_identifier:
                record = db.query(OfficialJournalAct).filter(
                    OfficialJournalAct.act_identifier == act_identifier
                ).first()
                if record and record.signature_identifier:
                    signature_identifier = record.signature_identifier
            else:
                series = extract_oj_series(source_reference)
                publication_day = doc.publication_date.date() if doc.publication_date else None
                if series and publication_day:
                    matches = db.query(OfficialJournalAct).filter(
                        OfficialJournalAct.publication_date == publication_day,
                        OfficialJournalAct.series == series,
                    ).all()
                    if len(matches) == 1:
                        record = matches[0]
                        act_identifier = record.act_identifier
                        signature_identifier = record.signature_identifier

            if not act_identifier and not signature_identifier:
                continue

            if act_identifier != doc.oj_act_identifier or signature_identifier != doc.oj_signature_identifier:
                updated += 1
                if not args.dry_run:
                    doc.oj_act_identifier = act_identifier
                    doc.oj_signature_identifier = signature_identifier

        if not args.dry_run:
            db.commit()

        print(
            f"✅ OJ backfill complete. scanned={seen} updated={updated} dry_run={args.dry_run}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
