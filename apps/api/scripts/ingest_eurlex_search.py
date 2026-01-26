"""
Ingest Eur-Lex search results for PSP/EMI/PSAN scope (FR+EN).
Metadata-only pass; full text can be extracted later in batches.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from typing import List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import settings
from src.database import SessionLocal
from src.ingestion.eurlex_search import EurLexSearchFetcher
from src.ingestion.processor import IngestionProcessor
from src.models import RegulatorySource, IngestionRun


def _parse_terms(value: str) -> List[str]:
    if not value:
        return []
    parts = [item.strip() for item in value.split(";") if item.strip()]
    return parts


def _expand_french_terms(terms: List[str]) -> List[str]:
    extra_terms = [
        "prestataire de services de paiement",
        "services de paiement",
        "etablissement de monnaie electronique",
        "monnaie electronique",
        "prestataire de services sur actifs numeriques",
        "actifs numeriques",
        "crypto-actifs",
        "psan",
        "mica",
        "\u00e9tablissement de monnaie \u00e9lectronique",
        "monnaie \u00e9lectronique",
        "prestataire de services sur actifs num\u00e9riques",
        "actifs num\u00e9riques",
    ]
    merged = []
    seen = set()
    for term in terms + extra_terms:
        normalized = term.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(normalized)
    return merged


def _parse_languages(value: str) -> List[str]:
    if not value:
        return ["en", "fr"]
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Eur-Lex search results (metadata only).")
    parser.add_argument("--languages", default=settings.EURLEX_LANGUAGES, help="Comma-separated languages (default: EURLEX_LANGUAGES)")
    parser.add_argument("--limit", type=int, default=settings.EURLEX_SEARCH_PAGE_SIZE, help="Page size per request")
    parser.add_argument("--max-pages", type=int, default=1, help="Max pages per language")
    parser.add_argument("--dry-run", action="store_true", help="Fetch without writing to database")
    parser.add_argument("--no-lang-filter", action="store_true", help="Disable language filter in SPARQL (fallback)")
    parser.add_argument("--terms-fr", default=settings.EURLEX_SEARCH_TERMS_FR, help="Semicolon-separated FR terms")
    parser.add_argument("--terms-en", default=settings.EURLEX_SEARCH_TERMS_EN, help="Semicolon-separated EN terms")
    args = parser.parse_args()

    languages = _parse_languages(args.languages)
    terms_fr = _expand_french_terms(_parse_terms(args.terms_fr))
    terms_en = _parse_terms(args.terms_en)

    fetcher = EurLexSearchFetcher()
    db = SessionLocal()
    processor = IngestionProcessor(db)

    try:
        for language in languages:
            terms = terms_fr if language == "fr" else terms_en
            source_key = f"eur-lex-search-{language}"
            source = db.query(RegulatorySource).filter(RegulatorySource.source_key == source_key).first()
            if not source:
                source = RegulatorySource(
                    source_key=source_key,
                    name=f"EUR-Lex Search ({language.upper()})",
                    jurisdiction="EU",
                    language=language,
                    source_type="search",
                    base_url="https://eur-lex.europa.eu/search.html",
                    schedule="manual",
                    metadata_json={"terms": terms},
                )
                db.add(source)
                db.commit()
            else:
                source.metadata_json = {"terms": terms}
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

            for page in range(args.max_pages):
                offset = page * args.limit
                results = fetcher.search_terms(
                    terms=terms,
                    language=language,
                    limit=args.limit,
                    offset=offset,
                    require_language=not args.no_lang_filter,
                )
                if not results and not args.no_lang_filter:
                    print(f"ℹ️ No results with language filter for {language.upper()} page {page+1}; retrying without language filter.")
                    results = fetcher.search_terms(
                        terms=terms,
                        language=language,
                        limit=args.limit,
                        offset=offset,
                        require_language=False,
                    )
                if not results:
                    break
                for metadata in results:
                    celex = (metadata.get("celex") or "").strip()
                    if not celex or not celex.startswith("3"):
                        continue
                    entry = fetcher.to_entry(metadata, language=language)
                    seen += 1
                    if args.dry_run:
                        continue
                    try:
                        result = processor.process_entry(entry)
                        if result == "new":
                            created += 1
                        elif result == "updated":
                            updated += 1
                    except Exception as exc:
                        errors.append({"error": str(exc), "entry": entry.get("link")})

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
                f"✅ {language.upper()} finished. seen={seen} new={created} updated={updated} errors={len(errors)}"
            )

    finally:
        db.close()


if __name__ == "__main__":
    main()
