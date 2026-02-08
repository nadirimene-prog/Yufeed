"""
Script to build RAG chunk index from legal documents.
"""

import sys

from src.database import SessionLocal
from src.ai.rag_indexer import RAGIndexer


def main() -> None:
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print("Usage: python -m scripts.build_rag_index [limit]")
            return

    db = SessionLocal()
    try:
        indexer = RAGIndexer(db)
        total = indexer.index_all_documents(limit=limit)
        print(f"✅ Indexed {total} chunks")
    finally:
        db.close()


if __name__ == "__main__":
    main()
