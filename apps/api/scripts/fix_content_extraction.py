#!/usr/bin/env python3
"""
Fix script to re-extract content for documents that failed extraction.

Usage:
    cd apps/api
    PYTHONPATH=src python3 scripts/fix_content_extraction.py [--dry-run] [--limit 100]
"""

import argparse
import sys
import os

# Add src to path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, "..", "src")
sys.path.insert(0, os.path.abspath(src_dir))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import settings
from src.models import LegalDocument, LegalDocumentText
from src.ingestion.content_extractor import ContentExtractor
from src.search import index_document
from src.ai.rag_indexer import RAGIndexer
from src.utils.time import utc_now
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def is_valid_eurlex_celex(celex: str) -> bool:
    """Check if CELEX looks like a valid EUR-Lex document (not national)."""
    if not celex:
        return False
    # Must start with digit (EU documents)
    if not celex[0].isdigit():
        return False
    # Must have type code at position 6 (R, L, D, etc.)
    if len(celex) < 6:
        return False
    type_code = celex[5]
    valid_types = {
        "R",
        "L",
        "D",
        "C",
        "E",
        "F",
        "S",
        "H",
        "J",
        "K",
        "M",
        "P",
        "T",
        "X",
        "A",
        "B",
        "G",
        "N",
    }
    return type_code in valid_types


def fix_content_extraction(dry_run: bool = True, limit: int = None, only_null: bool = True):
    """Re-extract content for documents without full_text."""

    # Setup DB
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    extractor = ContentExtractor()

    # Query documents without content
    query = db.query(LegalDocument)
    if only_null:
        query = query.filter(LegalDocument.full_text.is_(None))

    # Only valid EUR-Lex CELEX numbers
    docs = query.all()
    valid_docs = [d for d in docs if is_valid_eurlex_celex(d.celex)]

    if limit:
        valid_docs = valid_docs[:limit]

    logger.info(f"Found {len(valid_docs)} documents to process (from {len(docs)} total)")

    if dry_run:
        logger.info("DRY RUN - No changes will be made")
        for doc in valid_docs[:10]:
            logger.info(f"  Would process: {doc.celex} - {doc.title[:60]}...")
        if len(valid_docs) > 10:
            logger.info(f"  ... and {len(valid_docs) - 10} more")
        return

    # Process documents
    success_count = 0
    fail_count = 0

    for doc in valid_docs:
        logger.info(f"Processing {doc.celex}...")

        try:
            language = doc.primary_language or "en"
            content_result = extractor.extract_content(doc.celex, language=language)

            if not content_result or not content_result.get("full_text"):
                logger.warning(
                    f"  No content extracted (method: {content_result.get('extraction_method') if content_result else 'None'})"
                )
                fail_count += 1
                continue

            # Update document
            doc.full_text = content_result["full_text"]
            doc.article_breakdown = {"articles": content_result.get("article_breakdown", [])}
            doc.content_extraction_method = content_result.get("extraction_method")
            doc.content_extracted_at = utc_now()
            doc.word_count = content_result.get("word_count")
            doc.last_modified = utc_now()

            # Create/update LegalDocumentText
            doc_text = (
                db.query(LegalDocumentText)
                .filter(LegalDocumentText.doc_id == doc.id, LegalDocumentText.language == language)
                .first()
            )

            if doc_text:
                doc_text.full_text = content_result["full_text"]
                doc_text.article_breakdown = {
                    "articles": content_result.get("article_breakdown", [])
                }
                doc_text.content_extraction_method = content_result.get("extraction_method")
                doc_text.content_extracted_at = utc_now()
                doc_text.word_count = content_result.get("word_count")
            else:
                doc_text = LegalDocumentText(
                    doc_id=doc.id,
                    language=language,
                    full_text=content_result["full_text"],
                    article_breakdown={"articles": content_result.get("article_breakdown", [])},
                    content_extraction_method=content_result.get("extraction_method"),
                    content_extracted_at=utc_now(),
                    word_count=content_result.get("word_count"),
                    source_url=doc.source_reference,
                )
                db.add(doc_text)

            db.commit()
            logger.info(
                f"  ✅ Extracted {content_result.get('word_count')} words via {content_result.get('extraction_method')}"
            )
            success_count += 1

            # Index in OpenSearch
            try:
                index_document(doc)
                logger.info(f"    Indexed in OpenSearch")
            except Exception as e:
                logger.warning(f"    Failed to index in OpenSearch: {e}")

            # RAG index if enabled
            if settings.RAG_INDEX_ENABLED:
                try:
                    rag_indexer = RAGIndexer(db)
                    chunk_count = rag_indexer.index_document(doc)
                    logger.info(f"    Indexed {chunk_count} RAG chunks")
                except Exception as e:
                    logger.warning(f"    Failed to index RAG: {e}")

        except Exception as e:
            logger.error(f"  ❌ Error: {e}")
            fail_count += 1
            db.rollback()

    logger.info(f"\nDone! Success: {success_count}, Failed: {fail_count}")
    db.close()


def main():
    parser = argparse.ArgumentParser(description="Fix content extraction for documents")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done without making changes"
    )
    parser.add_argument("--limit", type=int, help="Limit number of documents to process")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all documents (not just those with null content)",
    )

    args = parser.parse_args()

    fix_content_extraction(dry_run=args.dry_run, limit=args.limit, only_null=not args.all)


if __name__ == "__main__":
    main()
