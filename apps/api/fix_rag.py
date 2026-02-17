import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

os.chdir("/Users/imenenadir/Documents/Yufeed/apps/api")

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./compliance.db")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

Base = declarative_base()


class LegalDocument(Base):
    __tablename__ = "legal_documents"
    id = Column(Integer, primary_key=True)
    celex = Column(String)
    title = Column(String)
    full_text = Column(Text)


class LegalChunk(Base):
    __tablename__ = "legal_chunks"
    id = Column(Integer, primary_key=True)
    chunk_id = Column(String)
    doc_id = Column(Integer)
    celex = Column(String)
    chunk_text = Column(Text)
    chunk_index = Column(Integer)


def simple_chunk(text, chunk_size=2000, overlap=200):
    """Simple chunking by paragraphs."""
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""
    chunk_idx = 0

    for para in paragraphs:
        if len(current_chunk) + len(para) > chunk_size:
            if current_chunk:
                chunks.append((chunk_idx, current_chunk.strip()))
                chunk_idx += 1
                # Keep overlap
                words = current_chunk.split()
                current_chunk = " ".join(words[-overlap // 10 :]) + "\n\n" + para
            else:
                current_chunk = para
        else:
            current_chunk += "\n\n" + para if current_chunk else para

    if current_chunk:
        chunks.append((chunk_idx, current_chunk.strip()))

    return chunks


print("Indexing documents into RAG...")

# Get documents with content
from sqlalchemy import func

docs = db.query(LegalDocument).filter(LegalDocument.full_text.isnot(None)).all()

print(f"Found {len(docs)} documents with content\n")

total_chunks = 0

for doc in docs:
    # Check if already indexed
    existing = db.query(func.count(LegalChunk.id)).filter(LegalChunk.doc_id == doc.id).scalar()
    if existing > 0:
        print(f"{doc.celex}: Already indexed ({existing} chunks)")
        continue

    print(f"{doc.celex}: Chunking...", end=" ")

    try:
        chunks = simple_chunk(doc.full_text or "")

        for idx, text in chunks:
            chunk = LegalChunk(
                chunk_id=f"{doc.celex}_{idx}",
                doc_id=doc.id,
                celex=doc.celex,
                chunk_text=text,
                chunk_index=idx,
            )
            db.add(chunk)

        db.commit()
        print(f"✓ {len(chunks)} chunks")
        total_chunks += len(chunks)

    except Exception as e:
        print(f"✗ Error: {str(e)[:40]}")
        db.rollback()

# Show final stats
chunk_count = db.query(func.count(LegalChunk.id)).scalar()
docs_indexed = db.query(func.count(func.distinct(LegalChunk.doc_id))).scalar()

db.close()

print(f"\n{'='*60}")
print(f"Total chunks created: {total_chunks}")
print(f"Total chunks in DB: {chunk_count}")
print(f"Documents indexed: {docs_indexed}")
