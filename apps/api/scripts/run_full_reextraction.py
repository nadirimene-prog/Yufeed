#!/usr/bin/env python3
"""
Full Batch Re-extraction - All remaining documents
"""

import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from tqdm import tqdm
import importlib.util

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Import new extractor
spec = importlib.util.spec_from_file_location(
    "extractor", str(Path(__file__).parent.parent / "src/ingestion/content_extractor_v2.py")
)
extractor_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extractor_module)
ContentExtractorV2 = extractor_module.ContentExtractorV2

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os


def get_database_url():
    possible_dbs = ["./compliance.db", "./src/compliance.db"]
    for db_path in possible_dbs:
        if os.path.exists(db_path):
            return f"sqlite:///{db_path}"
    return "sqlite:///./compliance.db"


DATABASE_URL = get_database_url()
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


def get_documents_needing_extraction(db):
    """Get all documents without good content."""
    result = db.execute(
        text(
            """
        SELECT id, celex, title, type, full_text
        FROM legal_documents
        WHERE full_text IS NULL OR LENGTH(full_text) < 1000
        ORDER BY RANDOM()
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
    print("FULL BATCH RE-EXTRACTION - ALL REMAINING DOCUMENTS")
    print("=" * 70)
    print(f"Database: {DATABASE_URL}")
    print(f"Started: {datetime.now().isoformat()}")

    db = Session()
    extractor = ContentExtractorV2()

    try:
        docs = get_documents_needing_extraction(db)
        total_docs = len(docs)
        print(f"\n📋 Found {total_docs} documents needing content extraction")

        if not docs:
            print("✅ All documents already have content!")
            return

        results = {
            "started_at": datetime.now().isoformat(),
            "total_attempted": 0,
            "successful": 0,
            "failed": 0,
            "total_words": 0,
            "errors": [],
            "by_strategy": {},
        }

        # Process all documents with progress bar
        for i, doc in enumerate(tqdm(docs, desc="Extracting content")):
            try:
                logger.info(f"[{i+1}/{total_docs}] Processing {doc['celex']}")

                result = extractor.extract(
                    celex=doc["celex"], title=doc["title"] or "", language="EN"
                )

                results["total_attempted"] += 1

                if result and result.word_count > 100:
                    update_document(db, doc["id"], result)
                    db.commit()
                    results["successful"] += 1
                    results["total_words"] += result.word_count

                    # Track by strategy
                    strategy = result.strategy
                    results["by_strategy"][strategy] = results["by_strategy"].get(strategy, 0) + 1

                    logger.info(f"✅ Success: {result.word_count} words via {strategy}")
                else:
                    results["failed"] += 1
                    results["errors"].append(
                        {
                            "celex": doc["celex"],
                            "title": doc["title"][:100] if doc["title"] else "",
                            "error": "No content extracted",
                        }
                    )
                    logger.warning(f"❌ Failed: No content")

                # Rate limiting - be nice to EUR-Lex
                time.sleep(0.3)

            except Exception as e:
                results["failed"] += 1
                error_msg = str(e)[:200]
                results["errors"].append(
                    {
                        "celex": doc["celex"],
                        "title": doc["title"][:100] if doc["title"] else "",
                        "error": error_msg,
                    }
                )
                logger.error(f"❌ Error: {error_msg}")
                db.rollback()
                continue

            # Save progress every 10 documents
            if (i + 1) % 10 == 0:
                with open("extraction_progress.json", "w") as f:
                    json.dump(
                        {
                            "processed": i + 1,
                            "successful": results["successful"],
                            "failed": results["failed"],
                            "success_rate": f"{(results['successful'] / max(results['total_attempted'], 1) * 100):.1f}%",
                        },
                        f,
                        indent=2,
                    )

        # Final stats
        results["completed_at"] = datetime.now().isoformat()

        print("\n" + "=" * 70)
        print("FINAL RESULTS")
        print("=" * 70)
        print(f"Total Attempted: {results['total_attempted']}")
        print(f"Successful: {results['successful']}")
        print(f"Failed: {results['failed']}")
        print(
            f"Success Rate: {(results['successful'] / max(results['total_attempted'], 1) * 100):.1f}%"
        )
        print(f"Total Words Extracted: {results['total_words']:,}")
        print(f"Average Words per Doc: {results['total_words'] // max(results['successful'], 1):,}")

        print("\nBy Strategy:")
        for strategy, count in results["by_strategy"].items():
            print(f"  {strategy}: {count}")

        # Save report
        report_path = Path("full_reextraction_report.json")
        with open(report_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Full report saved to: {report_path}")

    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user. Progress saved.")
        with open("extraction_progress.json", "w") as f:
            json.dump(
                {
                    "status": "interrupted",
                    "successful": results.get("successful", 0),
                    "failed": results.get("failed", 0),
                },
                f,
                indent=2,
            )
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
