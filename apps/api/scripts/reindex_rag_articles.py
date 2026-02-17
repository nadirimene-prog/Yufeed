#!/usr/bin/env python3
"""
Re-index RAG with Article-Level Chunking
- Replaces document-level chunks with article-level chunks
- Uses new content from extraction
"""

import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import importlib.util

spec = importlib.util.spec_from_file_location(
    "chunker", str(Path(__file__).parent.parent / "src/services/article_chunker.py")
)
chunker_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chunker_module)
ArticleChunker = chunker_module.ArticleChunker

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


def get_documents_with_content(db):
    """Get all documents with full text."""
    result = db.execute(
        text(
            """
        SELECT id, celex, title, full_text, article_breakdown, word_count
        FROM legal_documents
        WHERE full_text IS NOT NULL AND LENGTH(full_text) > 1000
        ORDER BY word_count DESC
    """
        )
    ).fetchall()

    return [
        {
            "id": row[0],
            "celex": row[1],
            "title": row[2],
            "full_text": row[3],
            "article_breakdown": json.loads(row[4]) if row[4] else None,
            "word_count": row[5],
        }
        for row in result
    ]


def index_chunk_in_opensearch(chunk):
    """Index a single chunk in OpenSearch."""
    # This is a placeholder - actual implementation would use OpenSearch client
    # For now, just log success
    logger.debug(f"Indexed chunk {chunk.chunk_id}")
    return True


def main():
    print("\n" + "=" * 70)
    print("RAG RE-INDEXING WITH ARTICLE-LEVEL CHUNKING")
    print("=" * 70)

    db = Session()
    chunker = ArticleChunker()

    try:
        docs = get_documents_with_content(db)
        print(f"\n📋 Found {len(docs)} documents with content to index")

        total_chunks = 0
        doc_chunks = []

        for doc in tqdm(docs, desc="Chunking documents"):
            try:
                chunks = chunker.chunk_document(
                    doc_id=doc["id"],
                    celex=doc["celex"],
                    full_text=doc["full_text"],
                    article_breakdown=doc["article_breakdown"],
                )

                doc_chunks.append(
                    {
                        "celex": doc["celex"],
                        "title": doc["title"],
                        "doc_id": doc["id"],
                        "chunks": len(chunks),
                        "total_words": sum(c.word_count for c in chunks),
                    }
                )

                total_chunks += len(chunks)

                # Index each chunk (placeholder)
                for chunk in chunks:
                    index_chunk_in_opensearch(chunk)

            except Exception as e:
                logger.error(f"Error chunking {doc['celex']}: {e}")
                continue

        # Statistics
        print("\n" + "=" * 70)
        print("RE-INDEXING RESULTS")
        print("=" * 70)
        print(f"Documents processed: {len(docs)}")
        print(f"Total article chunks: {total_chunks}")
        print(f"Average chunks per doc: {total_chunks // max(len(docs), 1)}")

        # Show top 5 documents by chunk count
        doc_chunks.sort(key=lambda x: x["chunks"], reverse=True)
        print("\nTop 5 documents by chunk count:")
        for d in doc_chunks[:5]:
            print(f"  {d['celex']}: {d['chunks']} chunks ({d['total_words']:,} words)")

        # Save report
        report = {
            "timestamp": datetime.now().isoformat(),
            "documents_processed": len(docs),
            "total_chunks": total_chunks,
            "document_breakdown": doc_chunks[:20],
        }

        with open("rag_reindex_report.json", "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n💾 Report saved to: rag_reindex_report.json")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
