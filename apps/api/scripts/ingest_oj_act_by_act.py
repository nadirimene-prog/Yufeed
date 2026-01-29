"""
Ingest Official Journal act-by-act records from EUR-Lex (Cellar SPARQL).
Stores act and signature identifiers for each publication date.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, timedelta, timezone
from typing import Iterable, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import settings
from src.database import SessionLocal
from src.ingestion.cellar import CellarClient
from src.models import RegulatorySource, IngestionRun, OfficialJournalAct


def _parse_date(value: Optional[str]) -> date:
    if not value:
        raise ValueError("Date value is required")
    return date.fromisoformat(value)


def _parse_series(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def _date_range(start_date: date, end_date: date, max_days: Optional[int]) -> Iterable[date]:
    if start_date > end_date:
        raise ValueError("start_date must be <= end_date")
    total_days = (end_date - start_date).days
    for day_offset in range(total_days + 1):
        if max_days is not None and day_offset >= max_days:
            break
        yield start_date + timedelta(days=day_offset)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Official Journal act-by-act records.")
    parser.add_argument("--start-date", default=getattr(settings, "EURLEX_OJ_START_DATE", "1999-01-01"))
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--max-days", type=int, default=None, help="Limit number of days (for testing)")
    parser.add_argument("--series", default=None, help="Comma-separated OJ series filter (default: all)")
    parser.add_argument("--dry-run", action="store_true", help="Fetch without writing to database")
    args = parser.parse_args()

    start_date = _parse_date(args.start_date)
    end_date = _parse_date(args.end_date) if args.end_date else datetime.now(timezone.utc).date()
    series_filter = _parse_series(args.series)

    db = SessionLocal()
    cellar = CellarClient()

    try:
        source_key = "eur-lex-oj-act-by-act"
        source = db.query(RegulatorySource).filter(RegulatorySource.source_key == source_key).first()
        metadata = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "series": series_filter or "all",
        }
        if not source:
            source = RegulatorySource(
                source_key=source_key,
                name="EUR-Lex Official Journal Act-by-Act",
                jurisdiction="EU",
                language="multi",
                source_type="sparql",
                base_url=CellarClient.SPARQL_ENDPOINT,
                schedule="manual",
                metadata_json=metadata,
            )
            db.add(source)
            db.commit()
        else:
            source.metadata_json = metadata
            db.commit()

        run = IngestionRun(
            source_id=source.id,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        db.add(run)
        db.commit()

        seen = 0
        created = 0
        updated = 0
        errors = []
        seen_identifiers = set()

        for current_date in _date_range(start_date, end_date, args.max_days):
            try:
                acts = cellar.search_oj_act_by_date(current_date)
            except Exception as exc:
                errors.append({"error": str(exc), "date": current_date.isoformat()})
                continue

            if not acts:
                continue

            for act in acts:
                act_identifier = act.get("act_identifier")
                if not act_identifier:
                    continue
                if act_identifier in seen_identifiers:
                    continue
                seen_identifiers.add(act_identifier)
                series = (act.get("series") or "").upper()
                if series_filter and series not in series_filter:
                    continue

                seen += 1
                if args.dry_run:
                    continue

                existing = db.query(OfficialJournalAct).filter(
                    OfficialJournalAct.act_identifier == act_identifier
                ).first()
                if not existing:
                    db.add(
                        OfficialJournalAct(
                            act_identifier=act_identifier,
                            act_uri=act.get("act_uri"),
                            signature_identifier=act.get("signature_identifier"),
                            signature_uri=act.get("signature_uri"),
                            publication_date=act.get("publication_date"),
                            series=series or None,
                        )
                    )
                    created += 1
                    continue

                changed = False
                if existing.signature_identifier != act.get("signature_identifier"):
                    existing.signature_identifier = act.get("signature_identifier")
                    changed = True
                if existing.signature_uri != act.get("signature_uri"):
                    existing.signature_uri = act.get("signature_uri")
                    changed = True
                if existing.act_uri != act.get("act_uri"):
                    existing.act_uri = act.get("act_uri")
                    changed = True
                if existing.publication_date != act.get("publication_date"):
                    existing.publication_date = act.get("publication_date")
                    changed = True
                if existing.series != (series or None):
                    existing.series = series or None
                    changed = True
                if changed:
                    updated += 1

            if not args.dry_run:
                db.commit()

        run.items_seen = seen
        run.items_new = created
        run.items_updated = updated
        run.errors_json = errors or None
        run.completed_at = datetime.now(timezone.utc)
        run.status = "failed" if errors else "completed"
        db.commit()

        source.last_ingested_at = run.completed_at
        db.commit()

        print(
            f"✅ OJ act-by-act finished. seen={seen} new={created} updated={updated} errors={len(errors)}"
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()
