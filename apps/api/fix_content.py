import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

os.chdir("/Users/imenenadir/Documents/Yufeed/apps/api")

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, or_
from sqlalchemy.orm import sessionmaker, declarative_base
import requests
from bs4 import BeautifulSoup
import re

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
    primary_language = Column(String)
    full_text = Column(Text)
    word_count = Column(Integer)
    content_extraction_method = Column(String)
    content_extracted_at = Column(DateTime)


def extract_from_eurlex_html(celex, language="EN"):
    """Extract content from EUR-Lex HTML endpoint."""
    url = f"https://eur-lex.europa.eu/legal-content/{language.upper()}/TXT/HTML/?uri=CELEX:{celex}"
    try:
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.content, "html.parser")

        # Find main content
        content_div = (
            soup.find("div", {"class": "eli-container"})
            or soup.find("div", {"id": "text"})
            or soup.find("div", {"class": "texte"})
            or soup.find("div", {"id": "TexteOnly"})
        )

        if not content_div:
            return None

        full_text = content_div.get_text(separator="\n", strip=True)
        full_text = re.sub(r"\n{3,}", "\n\n", full_text)
        full_text = re.sub(r" {2,}", " ", full_text)

        return {
            "full_text": full_text,
            "word_count": len(full_text.split()) if full_text else 0,
            "extraction_method": "eurlex_html",
        }
    except Exception as e:
        return None


print("Finding EU legislation documents...")

docs = (
    db.query(LegalDocument)
    .filter(
        LegalDocument.full_text.is_(None),
        or_(
            LegalDocument.celex.like("2%"),
            LegalDocument.celex.like("3%"),
            LegalDocument.celex.like("4%"),
        ),
    )
    .all()
)

print(f"Found {len(docs)} EU documents to process\n")

if not docs:
    print("No documents to process!")
    db.close()
    exit()

success = 0
failed = 0

for doc in docs[:15]:
    title_display = (
        (doc.title[:40] + "...") if doc.title and len(doc.title) > 40 else (doc.title or "No title")
    )
    print(f"{doc.celex}: {title_display}", end=" ")

    try:
        result = extract_from_eurlex_html(doc.celex, language=doc.primary_language or "en")
        if result and result.get("full_text"):
            doc.full_text = result["full_text"]
            doc.word_count = result["word_count"]
            doc.content_extraction_method = result["extraction_method"]
            from datetime import datetime

            doc.content_extracted_at = datetime.utcnow()
            db.commit()
            print(f"✓ {result['word_count']:,} words")
            success += 1
        else:
            print(f"✗ No content")
            failed += 1
    except Exception as e:
        print(f"✗ Error: {str(e)[:30]}")
        failed += 1

remaining = (
    db.query(LegalDocument)
    .filter(
        LegalDocument.full_text.is_(None),
        or_(
            LegalDocument.celex.like("2%"),
            LegalDocument.celex.like("3%"),
            LegalDocument.celex.like("4%"),
        ),
    )
    .count()
)

db.close()
print(f"\n{'='*60}")
print(f"Done! Success: {success}, Failed: {failed}")
print(f"Remaining EU docs without content: {remaining}")
if remaining > 0:
    print(f"Run again to process more")
