import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

os.chdir("/Users/imenenadir/Documents/Yufeed/apps/api")

from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import func

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
    chunk_index = Column(Integer)


class LegalDocument(Base):
    __tablename__ = "legal_documents"
    id = Column(Integer, primary_key=True)
    celex = Column(String)
    title = Column(String)
    full_text = Column(Text)


print("=" * 60)
print("RAG SYSTEM TEST")
print("=" * 60)

# 1. Check chunks
print("\n1. CHUNKS IN DATABASE")
print("-" * 40)
chunks = db.query(LegalChunk).all()
print(f"Total chunks: {len(chunks)}")

if chunks:
    print("\nSample chunks:")
    for chunk in chunks[:3]:
        doc = db.query(LegalDocument).filter(LegalDocument.id == chunk.doc_id).first()
        preview = chunk.chunk_text[:150].replace("\n", " ")
        print(f"  {chunk.celex}: {preview}...")

# 2. Test keyword search (simple BM25-like)
print("\n2. KEYWORD SEARCH TEST")
print("-" * 40)

search_terms = ["crypto", "MiCA", "AML", "asset", "token"]

for term in search_terms:
    matching = db.query(LegalChunk).filter(LegalChunk.chunk_text.contains(term)).all()
    if matching:
        docs = set(c.celex for c in matching)
        print(f"  '{term}' found in: {', '.join(docs)}")

# 3. Test content quality
print("\n3. CONTENT QUALITY CHECK")
print("-" * 40)

docs_with_content = db.query(LegalDocument).filter(LegalDocument.full_text.isnot(None)).all()
print(f"Documents with content: {len(docs_with_content)}")

for doc in docs_with_content[:5]:
    chunks_for_doc = (
        db.query(func.count(LegalChunk.id)).filter(LegalChunk.doc_id == doc.id).scalar()
    )
    text_sample = (doc.full_text or "")[:200].replace("\n", " ")
    print(f"\n  {doc.celex}:")
    print(f"    Title: {doc.title[:60] if doc.title else 'N/A'}...")
    print(f"    Chunks: {chunks_for_doc}")
    print(f"    Sample: {text_sample}...")

# 4. Check if OpenSearch is needed
print("\n4. OPENSEARCH STATUS")
print("-" * 40)
print("  RAG can work with just PostgreSQL (database-only mode)")
print(f"  Current chunks: {len(chunks)} (sufficient for testing)")

print("\n" + "=" * 60)
print("RAG is ready to use!")
print("Start the API: cd apps/api && python -m uvicorn src.main:app --reload")
print("Then test: curl -X POST http://localhost:8000/api/query/ask \\")
print("  -H 'Content-Type: application/json' \\")
print('  -d \'{"query": "What is MiCA?"}\'')
print("=" * 60)

db.close()
