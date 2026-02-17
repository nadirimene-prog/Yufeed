#!/usr/bin/env python3
"""
Batch Re-extraction Script
- Re-extracts content for all documents missing full_text
- Updates database with new content
- Reports on success rates
"""

import sys
import json
import time
from datetime import datetime
from pathlib import Path
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os


# Find correct database
def get_database_url():
    possible_dbs = [
        "./compliance.db",
        "./src/compliance.db",
    ]
    for db_path in possible_dbs:
        if os.path.exists(db_path):
            return f"sqlite:///{db_path}"
    return "sqlite:///./compliance.db"


DATABASE_URL = get_database_url()
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Import new extractor - bypass module imports
import importlib.util

spec = importlib.util.spec_from_file_location(
    "extractor", str(Path(__file__).parent.parent / "src/ingestion/content_extractor_v2.py")
)
extractor_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extractor_module)
ContentExtractorV2 = extractor_module.ContentExtractorV2


def get_documents_needing_extraction(db):
    """Get all documents without good content."""
    result = db.execute(
        text(
            """
        SELECT id, celex, title, type, full_text
        FROM legal_documents
        WHERE full_text IS NULL OR LENGTH(full_text) < 1000
        ORDER BY celex
    """
        )
    ).fetchall()

    return [
        {"id": row[0], "celex": row[1], "title": row[2], "type": row[3], "current_text": row[4]}
        for row in result
    ]


def update_document(db, doc_id, extraction_result):
    """Update document with extracted content."""
    db.execute(
        text(
            """
        UPDATE legal_documents
        SET full_text = :full_text,
            article_breakdown = :articles,
            word_count = :word_count,
            content_extraction_method = :method,
            content_extracted_at = :extracted_at
        WHERE id = :id
    """
        ),
        {
            "id": doc_id,
            "full_text": extraction_result.full_text,
            "articles": (
                json.dumps(extraction_result.articles) if extraction_result.articles else None
            ),
            "word_count": extraction_result.word_count,
            "method": extraction_result.strategy,
            "extracted_at": extraction_result.extracted_at,
        },
    )


def main():
    print("\n" + "=" * 70)
    print("BATCH RE-EXTRACTION")
    print("=" * 70)
    print(f"Database: {DATABASE_URL}")
    print(f"Started: {datetime.now().isoformat()}")

    db = Session()
    extractor = ContentExtractorV2()

    try:
        # Get documents needing extraction
        docs = get_documents_needing_extraction(db)
        print(f"\n📋 Found {len(docs)} documents needing content extraction")

        if not docs:
            print("✅ All documents already have content!")
            return

        # Process documents
        results = {"successful": 0, "failed": 0, "total_words": 0, "errors": []}

        for doc in tqdm(docs[:50], desc="Extracting content"):  # Limit to 50 for safety
            try:
                result = extractor.extract(
                    celex=doc["celex"], title=doc["title"] or "", language="EN"
                )

                if result and result.word_count > 100:
                    update_document(db, doc["id"], result)
                    db.commit()
                    results["successful"] += 1
                    results["total_words"] += result.word_count
                else:
                    results["failed"] += 1
                    results["errors"].append(
                        {"celex": doc["celex"], "error": "No content extracted"}
                    )

                # Rate limiting
                time.sleep(0.5)

            except Exception as e:
                results["failed"] += 1
                results["errors"].append({"celex": doc["celex"], "error": str(e)[:200]})
                db.rollback()
                continue

        # Final stats
        print("\n" + "=" * 70)
        print("RESULTS")
        print("=" * 70)
        print(f"Successful: {results['successful']}")
        print(f"Failed: {results['failed']}")
        print(f"Total words extracted: {results['total_words']:,}")
        print(f"Average words per doc: {results['total_words'] // max(results['successful'], 1):,}")

        # Save report
        report_path = Path("reextraction_report.json")
        with open(report_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Report saved to: {report_path}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
