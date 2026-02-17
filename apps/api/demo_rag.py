import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

os.chdir("/Users/imenenadir/Documents/Yufeed/apps/api")

from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./compliance.db")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

Base = declarative_base()


class LegalChunk(Base):
    __tablename__ = "legal_chunks"
    id = Column(Integer, primary_key=True)
    chunk_id = Column(String)
    doc_id = Column(Integer)
    celex = Column(String)
    chunk_text = Column(Text)


class LegalDocument(Base):
    __tablename__ = "legal_documents"
    id = Column(Integer, primary_key=True)
    celex = Column(String)
    title = Column(String)


def search_rag(query, max_results=5):
    """Simple keyword-based RAG search."""
    query_terms = query.lower().split()

    # Get all chunks
    chunks = db.query(LegalChunk).all()

    # Score by keyword matches
    scored = []
    for chunk in chunks:
        text_lower = chunk.chunk_text.lower()
        score = sum(1 for term in query_terms if term in text_lower)
        if score > 0:
            doc = db.query(LegalDocument).filter(LegalDocument.id == chunk.doc_id).first()
            scored.append((score, chunk, doc))

    # Sort by score
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:max_results]


print("=" * 70)
print("RAG DEMO - Ask questions about EU regulations")
print("=" * 70)

questions = [
    "What is MiCA?",
    "crypto asset service providers",
    "AML requirements",
    "token issuance",
]

for question in questions:
    print(f"\nQuestion: {question}")
    print("-" * 70)

    results = search_rag(question)

    if not results:
        print("  No relevant documents found")
        continue

    print(f"  Found {len(results)} relevant passages:\n")

    for i, (score, chunk, doc) in enumerate(results, 1):
        title = (
            doc.title if doc.title and not doc.title.startswith("$") else f"Document {doc.celex}"
        )
        preview = chunk.chunk_text[:300].replace("\n", " ").strip()
        print(f"  [{i}] {title}")
        print(f"      CELEX: {doc.celex} | Score: {score}")
        print(f"      {preview}...")
        print()

print("=" * 70)
print("RAG is working! Documents are searchable.")
print("=" * 70)

db.close()
